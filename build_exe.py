#!/usr/bin/env python3
"""
Script to create the application executable using PyInstaller.

Usage:
    python build_exe.py
    
Or directly with PyInstaller:
    pyinstaller --name="AI Local Manager" --windowed --onefile main.py
"""
import subprocess
import sys
import os

def build():
    """Build the executable."""
    print("🔨 Building AI Local Manager...")
    print("=" * 50)
    
    # Make sure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=AILocalManager",
        "--windowed",  # No console
        "--onefile",   # Single file
        "--clean",     # Clean cache
        "--noconfirm", # Don't ask for confirmation
        # Add data
        "--add-data=src:src",
        # Icon (if exists)
        # "--icon=assets/icon.ico",
        # Required hidden imports
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=requests",
        "--hidden-import=httpx",
        # Main file
        "main.py"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True)
        
        print()
        print("=" * 50)
        print("✅ Build completed successfully!")
        print()
        print("The executable is at: dist/AILocalManager.exe")
        print()
        print("Notes:")
        print("  - Make sure Ollama or LMStudio are installed")
        print("  - For AirLLM, install: pip install airllm torch")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ PyInstaller not found!")
        print("   Install with: pip install pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    build()
