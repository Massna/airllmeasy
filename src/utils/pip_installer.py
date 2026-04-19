"""Instalador de pacotes pip com progresso em tempo real (QThread + sinais).

Funciona tanto em execução normal (python main.py) quanto em executável
empacotado com PyInstaller (.exe).  Quando rodando como .exe, detecta e
usa o Python do sistema para invocar pip.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import QThread, Signal


# ---------------------------------------------------------------------------
# Detecção de Python quando rodando como .exe (PyInstaller)
# ---------------------------------------------------------------------------

def is_frozen() -> bool:
    """Retorna True se estamos rodando empacotado (PyInstaller, cx_Freeze, etc.)."""
    return getattr(sys, "frozen", False)


def _find_python_in_path() -> Optional[str]:
    """Procura python/python3 no PATH do sistema."""
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _find_python_in_common_locations() -> Optional[str]:
    """Tenta localizações comuns do Python no Windows."""
    candidates: List[Path] = []

    # Locais usuais do Python no Windows
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        programs = Path(local_app) / "Programs" / "Python"
        if programs.is_dir():
            for sub in sorted(programs.iterdir(), reverse=True):
                exe = sub / "python.exe"
                if exe.is_file():
                    candidates.append(exe)

    # py launcher do Windows
    py = shutil.which("py")
    if py:
        candidates.append(Path(py))

    # WindowsApps (Microsoft Store Python)
    apps = os.environ.get("LOCALAPPDATA", "")
    if apps:
        wapps = Path(apps) / "Microsoft" / "WindowsApps"
        for name in ("python3.exe", "python.exe"):
            p = wapps / name
            if p.is_file():
                candidates.append(p)

    for c in candidates:
        try:
            r = subprocess.run(
                [str(c), "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and "Python" in r.stdout:
                return str(c)
        except Exception:
            continue
    return None


def find_system_python() -> Tuple[Optional[str], Optional[str]]:
    """Encontra o interpretador Python do sistema.

    Retorna (caminho_python, site_packages_path) ou (None, erro).
    """
    if not is_frozen():
        # Rodando como script normal — usa o mesmo Python
        return sys.executable, None

    # Frozen: procura Python no sistema
    python = _find_python_in_path() or _find_python_in_common_locations()
    if python is None:
        return None, (
            "Python não encontrado no sistema.\n"
            "Instale o Python em python.org e marque 'Add to PATH'."
        )

    # Descobre o site-packages desse Python
    try:
        r = subprocess.run(
            [python, "-c", "import site; print(site.getsitepackages()[0])"],
            capture_output=True, text=True, timeout=10,
        )
        sp = r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        sp = None

    return python, sp


# ---------------------------------------------------------------------------
# Worker de instalação
# ---------------------------------------------------------------------------

class PipInstallWorker(QThread):
    """Executa ``pip install`` em background, emitindo progresso em tempo real.

    Sinais:
        progress_text  – texto de status ("Baixando airllm…", etc.)
        progress_pct   – porcentagem estimada 0–100 (–1 quando indeterminada)
        finished_ok    – emitido ao terminar: (sucesso: bool, mensagem: str)
        site_packages  – quando rodando como .exe, emite o caminho do
                         site-packages onde os pacotes foram instalados,
                         para que o app possa adicioná-lo ao sys.path.
    """

    progress_text = Signal(str)
    progress_pct = Signal(int)
    finished_ok = Signal(bool, str)
    site_packages = Signal(str)

    # ---------------------------------------------------------------------------
    # Regex para capturar progresso do pip
    # ---------------------------------------------------------------------------
    _RE_DOWNLOADING = re.compile(
        r"Downloading\s+(\S+?)[\s\-].*?\(([^)]+)\)", re.IGNORECASE
    )
    _RE_BAR = re.compile(
        r"[\s━╸]+?([\d.]+)\s*/\s*([\d.]+)\s*(kB|MB|GB)", re.IGNORECASE
    )
    _RE_INSTALLING = re.compile(r"Installing collected packages", re.IGNORECASE)
    _RE_SUCCESS = re.compile(r"Successfully installed", re.IGNORECASE)

    def __init__(
        self,
        packages: List[str],
        *,
        extra_args: Optional[List[str]] = None,
        label: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.packages = packages
        self.extra_args = extra_args or []
        self.label = label or ", ".join(packages)
        self._cancelled = False

    # ------------------------------------------------------------------
    def cancel(self):
        self._cancelled = True

    # ------------------------------------------------------------------
    def run(self):  # noqa: C901
        python, info = find_system_python()

        if python is None:
            self.finished_ok.emit(False, info or "Python não encontrado.")
            return

        # Quando rodando como .exe, avisa qual Python está usando
        if is_frozen():
            self.progress_text.emit(f"Usando Python do sistema: {python}")

        cmd = [
            python,
            "-m",
            "pip",
            "install",
            "--progress-bar=on",
            *self.extra_args,
            *self.packages,
        ]

        self.progress_text.emit(f"Iniciando instalação: {self.label}…")
        self.progress_pct.emit(-1)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as exc:
            self.finished_ok.emit(False, f"Falha ao iniciar pip: {exc}")
            return

        current_file = ""

        try:
            for raw_line in iter(proc.stdout.readline, ""):
                if self._cancelled:
                    proc.terminate()
                    self.finished_ok.emit(False, "Instalação cancelada pelo usuário.")
                    return

                line = raw_line.strip()
                if not line:
                    continue

                # Detecta qual arquivo está sendo baixado
                m_dl = self._RE_DOWNLOADING.search(line)
                if m_dl:
                    current_file = m_dl.group(1).split("/")[-1]
                    total_size = m_dl.group(2)
                    self.progress_text.emit(
                        f"Baixando {current_file} ({total_size})…"
                    )
                    self.progress_pct.emit(-1)
                    continue

                # Barra de progresso do pip (━━━━)
                m_bar = self._RE_BAR.search(line)
                if m_bar:
                    done = float(m_bar.group(1))
                    total = float(m_bar.group(2))
                    unit = m_bar.group(3)
                    if total > 0:
                        pct = int(done / total * 100)
                        self.progress_pct.emit(min(pct, 100))
                        self.progress_text.emit(
                            f"Baixando {current_file}: {done:.1f}/{total:.1f} {unit}"
                        )
                    continue

                if self._RE_INSTALLING.search(line):
                    self.progress_text.emit("Instalando pacotes…")
                    self.progress_pct.emit(90)
                    continue

                if self._RE_SUCCESS.search(line):
                    self.progress_text.emit("Instalação concluída!")
                    self.progress_pct.emit(100)
                    continue

            proc.stdout.close()
            ret = proc.wait()

        except Exception as exc:
            self.finished_ok.emit(False, f"Erro durante instalação: {exc}")
            return

        if ret == 0:
            # Emite o site-packages para o app adicionar ao sys.path
            if info:
                self.site_packages.emit(info)
            else:
                # Tenta descobrir o site-packages após instalar
                try:
                    r = subprocess.run(
                        [python, "-c", "import site; print(site.getsitepackages()[0])"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        self.site_packages.emit(r.stdout.strip())
                except Exception:
                    pass

            self.finished_ok.emit(True, f"{self.label} instalado(s) com sucesso!")
        else:
            self.finished_ok.emit(
                False,
                f"pip retornou código {ret}. Verifique a conexão e permissões.",
            )
