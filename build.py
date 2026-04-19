#!/usr/bin/env python3
"""
Build script for AirLLMEasy — creates a standalone executable
using PyInstaller for Windows, Linux, or macOS.

Usage:
    python build.py              # auto-detects the current OS
    python build.py --console    # keep terminal window (useful for debugging)

Or directly with PyInstaller:
    pyinstaller AILocalManager.spec
"""
import argparse
import platform
import subprocess
import sys
import os


def _data_separator() -> str:
    """PyInstaller uses ':' on Linux/macOS and ';' on Windows."""
    return ";" if platform.system() == "Windows" else ":"


def _output_name() -> str:
    """Final binary name shown to the user (platform-dependent)."""
    system = platform.system()
    if system == "Windows":
        return "dist/AILocalManager.exe"
    elif system == "Darwin":
        return "dist/AILocalManager.app  (or dist/AILocalManager)"
    else:
        return "dist/AILocalManager"


def build(*, console: bool = False):
    """Build the executable for the current platform."""
    system = platform.system()
    print(f"🔨 Building AirLLMEasy for {system}...")
    print("=" * 55)

    # Make sure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    sep = _data_separator()

    # --- PyInstaller command -------------------------------------------
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=AILocalManager",
        "--onefile",       # Single file
        "--clean",         # Clean cache
        "--noconfirm",     # Don't ask for confirmation
        f"--add-data=src{sep}src",
        # Required hidden imports
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=requests",
        "--hidden-import=httpx",
    ]

    # Windowed vs console mode
    if console:
        cmd.append("--console")
    else:
        cmd.append("--windowed")  # No terminal window

    # Platform-specific tweaks
    if system == "Windows":
        # Icon (if exists)
        icon = os.path.join(script_dir, "assets", "icon.ico")
        if os.path.isfile(icon):
            cmd.append(f"--icon={icon}")
    elif system == "Linux":
        # Strip debug symbols to reduce binary size
        cmd.append("--strip")
        # Icon for .desktop files (PNG format)
        icon = os.path.join(script_dir, "assets", "icon.png")
        if os.path.isfile(icon):
            cmd.append(f"--icon={icon}")
    elif system == "Darwin":
        cmd.append("--strip")
        icon = os.path.join(script_dir, "assets", "icon.icns")
        if os.path.isfile(icon):
            cmd.append(f"--icon={icon}")

    # Main entry point
    cmd.append("main.py")

    print(f"Running: {' '.join(cmd)}")
    print()

    try:
        subprocess.run(cmd, check=True)

        print()
        print("=" * 55)
        print("✅ Build completed successfully!")
        print()
        print(f"   Output: {_output_name()}")
        print()
        print("Notes:")
        print("  - Make sure Ollama or LMStudio are installed")
        print("  - For AirLLM, install: pip install airllm torch")

        # Linux: generate a .desktop file for convenience
        if system == "Linux":
            _generate_desktop_file(script_dir)

    except subprocess.CalledProcessError as e:
        print(f"❌ Build error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ PyInstaller not found!")
        print("   Install with: pip install pyinstaller")
        sys.exit(1)


def _generate_desktop_file(project_dir: str):
    """Create a .desktop launcher (freedesktop.org) next to the binary."""
    desktop_path = os.path.join(project_dir, "dist", "AILocalManager.desktop")
    icon_path = os.path.join(project_dir, "assets", "icon.png")
    has_icon = os.path.isfile(icon_path)

    content = f"""\
[Desktop Entry]
Name=AirLLMEasy
Comment=Manage and run AI models locally
Exec={os.path.join(project_dir, 'dist', 'AILocalManager')}
{'Icon=' + os.path.abspath(icon_path) if has_icon else '# Icon=path/to/icon.png'}
Terminal=false
Type=Application
Categories=Utility;Development;Science;
"""
    try:
        with open(desktop_path, "w") as f:
            f.write(content)
        os.chmod(desktop_path, 0o755)
        print()
        print(f"📄 Desktop launcher created: {desktop_path}")
        print("   Copy it to ~/.local/share/applications/ to add to your app menu.")
    except OSError:
        pass  # Non-critical


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build AirLLMEasy executable")
    parser.add_argument(
        "--console", action="store_true",
        help="Keep the terminal window visible (useful for debugging)",
    )
    args = parser.parse_args()
    build(console=args.console)
