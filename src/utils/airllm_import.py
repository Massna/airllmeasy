"""Ajusta sys.path para localizar o pacote Python airllm (incl. instalações editáveis via .pth).

Inclui auto-detecção automática que varre Python(s) do sistema, venvs, e
caminhos comuns para encontrar o pacote airllm sem intervenção do usuário.
"""
from __future__ import annotations

import glob
import importlib
import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

_log = logging.getLogger(__name__)

_last_inserted_paths: List[str] = []
_configured_packages_path: Optional[str] = None


def _has_airllm_package(site_or_parent: Path) -> bool:
    """Verifica se existe um pacote importável airllm diretamente sob este diretório."""
    try:
        for child in site_or_parent.iterdir():
            if not child.is_dir():
                continue
            if child.name.lower() != "airllm":
                continue
            init_py = child / "__init__.py"
            if init_py.is_file():
                return True
            # namespace ou só .pyd — aceita pasta airllm com algum .py
            if any(child.glob("*.py")):
                return True
    except OSError:
        pass
    return False


def _find_airllm_parent_walk_up(start: Path, max_up: int = 8) -> Optional[Path]:
    cur = start
    for _ in range(max_up):
        if _has_airllm_package(cur):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _find_airllm_shallow_search(root: Path, max_depth: int = 4, max_visits: int = 400) -> Optional[Path]:
    """Busca limitada por site-packages com airllm (ancestral do venv ou pasta ampla)."""
    budget = [max_visits]

    def scan(d: Path, depth: int) -> Optional[Path]:
        if depth > max_depth:
            return None
        budget[0] -= 1
        if budget[0] < 0:
            return None
        try:
            if _has_airllm_package(d):
                return d
            for sub in d.iterdir():
                if not sub.is_dir() or sub.name.startswith("."):
                    continue
                found = scan(sub, depth + 1)
                if found is not None:
                    return found
        except OSError:
            pass
        return None

    try:
        # Evita varrer pastas enormes (ex.: raiz do usuário com milhares de itens)
        try:
            n = sum(1 for _ in root.iterdir())
            if n > 64:
                return None
        except OSError:
            return None
        return scan(root.resolve(), 0)
    except OSError:
        return None


def resolve_airllm_site_packages(user_path: str) -> Optional[Path]:
    """
    Resolve até o diretório que deve entrar no sys.path (pai do pacote airllm).

    Aceita site-packages, pasta airllm, raiz do venv, ou pastas acima (sobe diretórios).
    """
    raw = (user_path or "").strip()
    if not raw:
        return None

    try:
        p = Path(raw).expanduser().resolve()
    except OSError:
        return None
    if not p.is_dir():
        return None

    # Usuário selecionou .../site-packages/airllm
    if p.name.lower() == "airllm" and p.parent.is_dir():
        if _has_airllm_package(p.parent):
            return p.parent

    if _has_airllm_package(p):
        return p

    if platform.system() == "Windows":
        cand = p / "Lib" / "site-packages"
        if cand.is_dir() and _has_airllm_package(cand):
            return cand
    else:
        for lib in p.glob("lib/python*/site-packages"):
            if lib.is_dir() and _has_airllm_package(lib):
                return lib
        for lib in glob.glob(str(p / "lib" / "python*" / "site-packages")):
            lp = Path(lib)
            if lp.is_dir() and _has_airllm_package(lp):
                return lp

    up = _find_airllm_parent_walk_up(p)
    if up is not None:
        return up

    shallow = _find_airllm_shallow_search(p, max_depth=4)
    if shallow is not None:
        return shallow

    return None


def _parse_pth_file(pth_file: Path, site_packages: Path, out: List[Path]) -> None:
    try:
        text = pth_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("import "):
            continue
        path = Path(line)
        if not path.is_absolute():
            path = (site_packages / path).resolve()
        else:
            path = path.resolve()
        if path.is_dir():
            out.append(path)


def _parse_egg_link(egg_link: Path, out: List[Path]) -> None:
    try:
        first = egg_link.read_text(encoding="utf-8", errors="ignore").splitlines()[0].strip()
    except (OSError, IndexError):
        return
    path = Path(first)
    if path.is_dir():
        out.append(path.resolve())


def collect_editable_and_pth_paths(site_packages: Path) -> List[Path]:
    """
    Caminhos extras declarados em .pth e .egg-link dentro de site-packages.
    Necessário porque o Python só aplica .pth na inicialização — não após mudar sys.path em runtime.
    """
    extra: List[Path] = []
    if not site_packages.is_dir():
        return extra
    try:
        for item in site_packages.iterdir():
            if item.name.startswith("."):
                continue
            if item.suffix == ".pth" and item.is_file():
                _parse_pth_file(item, site_packages, extra)
            elif item.suffix == ".egg-link" and item.is_file():
                _parse_egg_link(item, extra)
    except OSError:
        pass
    seen: set[str] = set()
    unique: List[Path] = []
    for ep in extra:
        s = str(ep)
        if s not in seen:
            seen.add(s)
            unique.append(ep)
    return unique


def _remove_tracked_from_syspath() -> None:
    for sp in _last_inserted_paths:
        while sp in sys.path:
            try:
                sys.path.remove(sp)
            except ValueError:
                break


def apply_airllm_packages_path(user_path: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Insere no sys.path o site-packages e caminhos de instalação editável (.pth / .egg-link).

    Retorna (ok, caminho site-packages resolvido ou None).
    """
    global _last_inserted_paths

    _remove_tracked_from_syspath()
    _last_inserted_paths = []

    if not user_path or not str(user_path).strip():
        importlib.invalidate_caches()
        return False, None

    resolved = resolve_airllm_site_packages(str(user_path))
    if not resolved:
        importlib.invalidate_caches()
        return False, None

    extras = collect_editable_and_pth_paths(resolved)

    # Ordem: primeiro os caminhos do .pth (código font do editable), depois site-packages.
    for ep in reversed(extras):
        s = str(ep)
        if s not in sys.path:
            sys.path.insert(0, s)
        _last_inserted_paths.append(s)

    sp = str(resolved)
    if sp not in sys.path:
        sys.path.insert(0, sp)
    _last_inserted_paths.append(sp)

    importlib.invalidate_caches()
    return True, sp


def set_airllm_packages_path(user_path: Optional[str]) -> Tuple[bool, Optional[str]]:
    global _configured_packages_path
    _configured_packages_path = (user_path or "").strip() or None
    return apply_airllm_packages_path(_configured_packages_path)


def ensure_airllm_path() -> None:
    apply_airllm_packages_path(_configured_packages_path)


def try_import_airllm() -> Tuple[bool, Optional[str]]:
    """
    Tenta importar airllm após aplicar o path configurado.
    Retorna (sucesso, mensagem de erro ou None).
    """
    ensure_airllm_path()
    try:
        import airllm  # noqa: F401
        return True, None
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Auto-detecção do pacote airllm
# ---------------------------------------------------------------------------

def _find_all_python_executables() -> List[str]:
    """Descobre todos os interpretadores Python disponíveis no sistema."""
    found: List[str] = []
    seen: set[str] = set()

    def _add(path: Optional[str]) -> None:
        if path is None:
            return
        try:
            resolved = str(Path(path).resolve())
        except OSError:
            return
        if resolved not in seen:
            seen.add(resolved)
            found.append(path)

    # 1) O próprio interpretador atual
    _add(sys.executable)

    # 2) python / python3 no PATH
    for name in ("python", "python3"):
        _add(shutil.which(name))

    # 3) py launcher (Windows)
    if platform.system() == "Windows":
        py = shutil.which("py")
        if py:
            _add(py)
            # py -0p lista todas as versões instaladas
            try:
                r = subprocess.run(
                    [py, "-0p"],
                    capture_output=True, text=True, timeout=5,
                )
                if r.returncode == 0:
                    for line in r.stdout.splitlines():
                        # Formato: " -3.12-64  C:\Python312\python.exe"
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            candidate = parts[-1].strip("*")
                            if Path(candidate).is_file():
                                _add(candidate)
            except Exception:
                pass

        # 4) Locais comuns do Python no Windows
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            programs = Path(local_app) / "Programs" / "Python"
            if programs.is_dir():
                for sub in sorted(programs.iterdir(), reverse=True):
                    exe = sub / "python.exe"
                    if exe.is_file():
                        _add(str(exe))

        # WindowsApps (Microsoft Store)
        if local_app:
            wapps = Path(local_app) / "Microsoft" / "WindowsApps"
            for name in ("python3.exe", "python.exe"):
                p = wapps / name
                if p.is_file():
                    _add(str(p))

    # 5) Conda envs
    for env_var in ("CONDA_PREFIX", "CONDA_EXE"):
        val = os.environ.get(env_var, "").strip()
        if not val:
            continue
        conda_root = Path(val)
        # CONDA_EXE aponta para o executável, subir até a raiz
        if conda_root.is_file():
            conda_root = conda_root.parent.parent
        envs_dir = conda_root / "envs"
        if envs_dir.is_dir():
            try:
                for env_dir in envs_dir.iterdir():
                    if not env_dir.is_dir():
                        continue
                    if platform.system() == "Windows":
                        exe = env_dir / "python.exe"
                    else:
                        exe = env_dir / "bin" / "python"
                    if exe.is_file():
                        _add(str(exe))
            except OSError:
                pass

    return found


def _pip_show_airllm(python_exe: str) -> Optional[Path]:
    """Executa 'pip show airllm' com o Python dado e retorna o Location."""
    try:
        r = subprocess.run(
            [python_exe, "-m", "pip", "show", "airllm"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            if line.lower().startswith("location:"):
                loc = line.split(":", 1)[1].strip()
                p = Path(loc)
                if p.is_dir() and _has_airllm_package(p):
                    return p
    except Exception:
        pass
    return None


def _scan_common_venv_locations() -> List[Path]:
    """Retorna site-packages de venvs em locais comuns perto do projeto."""
    candidates: List[Path] = []
    home = Path.home()

    # Locais onde desenvolvedores costumam criar venvs
    venv_names = ("venv", ".venv", "env", ".env", "airllm-env", "airllm_env")

    # Perto do executável / script
    base_dirs: List[Path] = []
    try:
        base_dirs.append(Path(sys.executable).resolve().parent)
    except Exception:
        pass
    try:
        base_dirs.append(Path(__file__).resolve().parent.parent.parent)  # raiz do projeto
    except Exception:
        pass
    base_dirs.append(Path.cwd())
    base_dirs.append(home)

    seen: set[str] = set()
    for base in base_dirs:
        for vname in venv_names:
            venv_root = base / vname
            if not venv_root.is_dir():
                continue
            if platform.system() == "Windows":
                sp = venv_root / "Lib" / "site-packages"
            else:
                # lib/python3.X/site-packages
                for sp_candidate in venv_root.glob("lib/python*/site-packages"):
                    sp = sp_candidate
                    break
                else:
                    continue
            if sp.is_dir():
                key = str(sp.resolve())
                if key not in seen:
                    seen.add(key)
                    candidates.append(sp)

    return candidates


def auto_detect_airllm_path() -> Optional[str]:
    """Tenta encontrar automaticamente onde o pacote airllm está instalado.

    Estratégias (em ordem de prioridade):
      1. Import direto (já está no sys.path)
      2. ``pip show airllm`` em cada Python encontrado no sistema
      3. Varredura de venvs em locais comuns
      4. Varredura de site-packages do(s) Python(s) encontrados

    Retorna o caminho da pasta que deve ser adicionada ao sys.path
    (geralmente o site-packages), ou None se não encontrou.
    """
    # 1) Já importável?
    try:
        import airllm  # noqa: F401
        # Já funciona — retorna o diretório pai do pacote
        pkg_dir = Path(airllm.__file__).resolve().parent.parent
        _log.info("auto_detect: airllm já importável em %s", pkg_dir)
        return str(pkg_dir)
    except Exception:
        pass

    # 2) pip show em cada Python
    pythons = _find_all_python_executables()
    for py in pythons:
        loc = _pip_show_airllm(py)
        if loc is not None:
            _log.info("auto_detect: pip show encontrou airllm em %s (via %s)", loc, py)
            return str(loc)

    # 3) Venvs em locais comuns
    for sp in _scan_common_venv_locations():
        if _has_airllm_package(sp):
            _log.info("auto_detect: airllm encontrado em venv %s", sp)
            return str(sp)

    # 4) site-packages de cada Python encontrado
    for py in pythons:
        try:
            r = subprocess.run(
                [py, "-c", "import site; print('\\n'.join(site.getsitepackages()))"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    sp = Path(line.strip())
                    if sp.is_dir() and _has_airllm_package(sp):
                        _log.info("auto_detect: airllm em site-packages %s (via %s)", sp, py)
                        return str(sp)
        except Exception:
            continue

    _log.info("auto_detect: airllm não encontrado em nenhum local")
    return None


def auto_detect_and_apply() -> Tuple[bool, Optional[str]]:
    """Executa auto-detecção e aplica o caminho encontrado.

    Retorna (encontrou: bool, caminho: str | None).
    """
    path = auto_detect_airllm_path()
    if path is None:
        return False, None

    ok, resolved = apply_airllm_packages_path(path)
    if ok:
        return True, resolved or path

    # Mesmo sem confirmar resolução, testa import
    try:
        import airllm  # noqa: F401
        return True, path
    except Exception:
        pass

    return False, None
