#!/usr/bin/env python3
"""
Script para criar o executável da aplicação usando PyInstaller.

Uso:
    python build_exe.py
    
Ou diretamente com PyInstaller:
    pyinstaller --name="AI Local Manager" --windowed --onefile main.py
"""
import subprocess
import sys
import os

def build():
    """Constrói o executável."""
    print("🔨 Construindo AI Local Manager...")
    print("=" * 50)
    
    # Garante que estamos no diretório correto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=AILocalManager",
        "--windowed",  # Sem console
        "--onefile",   # Um único arquivo
        "--clean",     # Limpa cache
        "--noconfirm", # Não pede confirmação
        # Adiciona dados
        "--add-data=src:src",
        # Ícone (se existir)
        # "--icon=assets/icon.ico",
        # Hidden imports necessários
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=requests",
        "--hidden-import=httpx",
        # Arquivo principal
        "main.py"
    ]
    
    print(f"Executando: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True)
        
        print()
        print("=" * 50)
        print("✅ Build concluído com sucesso!")
        print()
        print("O executável está em: dist/AILocalManager.exe")
        print()
        print("Notas:")
        print("  - Certifique-se de que Ollama ou LMStudio estão instalados")
        print("  - Para AirLLM, instale: pip install airllm torch")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no build: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ PyInstaller não encontrado!")
        print("   Instale com: pip install pyinstaller")
        sys.exit(1)


if __name__ == "__main__":
    build()
