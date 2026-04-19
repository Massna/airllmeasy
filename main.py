#!/usr/bin/env python3
"""
AI Local Manager - Aplicação para gerenciar e executar modelos de IA localmente.

Backends suportados:
- Ollama (Opção A): Download e execução de modelos
- LMStudio (Opção B): Download de GGUF e execução
- AirLLM: Execução otimizada para pouca memória
"""
import sys
import os

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.ui.main_window import MainWindow
from src.utils.config import Config
from src.utils.airllm_import import set_airllm_packages_path


def main():
    """Função principal da aplicação."""
    # Habilita High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Cria aplicação
    app = QApplication(sys.argv)
    app.setApplicationName("AI Local Manager")
    app.setOrganizationName("AILocalManager")
    app.setApplicationVersion("1.0.0")
    
    # Fonte padrão
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Carrega configurações
    config = Config()
    set_airllm_packages_path(config.airllm_packages_path)

    # Cria e mostra janela principal
    window = MainWindow(config)
    window.show()
    
    # Executa loop de eventos
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
