#!/usr/bin/env python3
"""
AirLLMEasy - Application for managing and running AI models locally.

Supported backends:
- Ollama (Option A): Download and run models
- LMStudio (Option B): Download GGUF files and run
- AirLLM: Memory-optimized execution
"""
import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.ui.main_window import MainWindow
from src.utils.config import Config
from src.utils.airllm_import import (
    set_airllm_packages_path,
    try_import_airllm,
    auto_detect_and_apply,
)


def main():
    """Main application function."""
    # Enable High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("AirLLMEasy")
    app.setOrganizationName("AILocalManager")
    app.setApplicationVersion("1.0.0")
    
    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Load settings
    config = Config()
    set_airllm_packages_path(config.airllm_packages_path)

    # Auto-detection: if airllm is not importable, try to find it automatically
    ok, _ = try_import_airllm()
    if not ok:
        found, detected_path = auto_detect_and_apply()
        if found and detected_path:
            # Save the detected path so we don't need to scan again
            config.airllm_packages_path = detected_path
            config.save()
            print(f"[auto-detect] AirLLM found at: {detected_path}")

    # Create and show main window
    window = MainWindow(config)
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
