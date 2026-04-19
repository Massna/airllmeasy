"""Pip package installer with real-time progress (QThread + signals).

Works both in normal execution (python main.py) and in a bundled
executable created with PyInstaller (.exe). When running as .exe,
detects and uses the system Python to invoke pip.
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
# Detecting Python when running as .exe (PyInstaller)
# ---------------------------------------------------------------------------

def is_frozen() -> bool:
    """Returns True if running as a bundled package (PyInstaller, cx_Freeze, etc.)."""
    return getattr(sys, "frozen", False)


def _find_python_in_path() -> Optional[str]:
    """Searches for python/python3 in the system PATH."""
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _find_python_in_common_locations() -> Optional[str]:
    """Tries common Python installation locations on Windows."""
    candidates: List[Path] = []

    # Common Python locations on Windows
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        programs = Path(local_app) / "Programs" / "Python"
        if programs.is_dir():
            for sub in sorted(programs.iterdir(), reverse=True):
                exe = sub / "python.exe"
                if exe.is_file():
                    candidates.append(exe)

    # Windows py launcher
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
    """Finds the system Python interpreter.

    Returns (python_path, site_packages_path) or (None, error_message).
    """
    if not is_frozen():
        # Running as a normal script — use the same Python
        return sys.executable, None

    # Frozen: search for Python on the system
    python = _find_python_in_path() or _find_python_in_common_locations()
    if python is None:
        return None, (
            "Python not found on the system.\n"
            "Install Python from python.org and check 'Add to PATH'."
        )

    # Find the site-packages for this Python
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
# Installation worker
# ---------------------------------------------------------------------------

class PipInstallWorker(QThread):
    """Runs ``pip install`` in background, emitting real-time progress.

    Signals:
        progress_text  – status text ("Downloading airllm…", etc.)
        progress_pct   – estimated percentage 0–100 (–1 when indeterminate)
        finished_ok    – emitted on completion: (success: bool, message: str)
        site_packages  – when running as .exe, emits the site-packages path
                         where the packages were installed, so the app can
                         add it to sys.path.
    """

    progress_text = Signal(str)
    progress_pct = Signal(int)
    finished_ok = Signal(bool, str)
    site_packages = Signal(str)

    # ---------------------------------------------------------------------------
    # Regex to capture pip progress
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
            self.finished_ok.emit(False, info or "Python not found.")
            return

        # When running as .exe, report which Python is being used
        if is_frozen():
            self.progress_text.emit(f"Using system Python: {python}")

        cmd = [
            python,
            "-m",
            "pip",
            "install",
            "--progress-bar=on",
            *self.extra_args,
            *self.packages,
        ]

        self.progress_text.emit(f"Starting installation: {self.label}…")
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
            self.finished_ok.emit(False, f"Failed to start pip: {exc}")
            return

        current_file = ""

        try:
            for raw_line in iter(proc.stdout.readline, ""):
                if self._cancelled:
                    proc.terminate()
                    self.finished_ok.emit(False, "Installation cancelled by user.")
                    return

                line = raw_line.strip()
                if not line:
                    continue

                # Detect which file is being downloaded
                m_dl = self._RE_DOWNLOADING.search(line)
                if m_dl:
                    current_file = m_dl.group(1).split("/")[-1]
                    total_size = m_dl.group(2)
                    self.progress_text.emit(
                        f"Downloading {current_file} ({total_size})…"
                    )
                    self.progress_pct.emit(-1)
                    continue

                # Pip progress bar (━━━━)
                m_bar = self._RE_BAR.search(line)
                if m_bar:
                    done = float(m_bar.group(1))
                    total = float(m_bar.group(2))
                    unit = m_bar.group(3)
                    if total > 0:
                        pct = int(done / total * 100)
                        self.progress_pct.emit(min(pct, 100))
                        self.progress_text.emit(
                            f"Downloading {current_file}: {done:.1f}/{total:.1f} {unit}"
                        )
                    continue

                if self._RE_INSTALLING.search(line):
                    self.progress_text.emit("Installing packages…")
                    self.progress_pct.emit(90)
                    continue

                if self._RE_SUCCESS.search(line):
                    self.progress_text.emit("Installation complete!")
                    self.progress_pct.emit(100)
                    continue

            proc.stdout.close()
            ret = proc.wait()

        except Exception as exc:
            self.finished_ok.emit(False, f"Error during installation: {exc}")
            return

        if ret == 0:
            # Emit the site-packages path for the app to add to sys.path
            if info:
                self.site_packages.emit(info)
            else:
                # Try to discover site-packages after install
                try:
                    r = subprocess.run(
                        [python, "-c", "import site; print(site.getsitepackages()[0])"],
                        capture_output=True, text=True, timeout=10,
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        self.site_packages.emit(r.stdout.strip())
                except Exception:
                    pass

            self.finished_ok.emit(True, f"{self.label} installed successfully!")
        else:
            self.finished_ok.emit(
                False,
                f"pip returned code {ret}. Check your connection and permissions.",
            )
