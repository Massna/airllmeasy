# 🤖 AI Local Manager

Aplicação desktop para gerenciar e executar modelos de IA localmente.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Funcionalidades

- **📥 Download de Modelos**: Suporte a Ollama e LMStudio
- **💬 Chat com IA**: Converse com modelos locais
- **🚀 AirLLM**: Execute modelos grandes com pouca memória
- **⚙️ Configurável**: Alterne entre backends facilmente
- **🎨 Interface Moderna**: Tema escuro elegante

## 🔧 Backends Suportados

### Opção A - Ollama
- Download direto do registro Ollama
- Execução nativa otimizada
- Modelos: Llama, Mistral, CodeLlama, Phi, etc.

### Opção B - LMStudio
- Download de arquivos GGUF do HuggingFace
- Interface API compatível com OpenAI
- Ótimo para modelos quantizados

### AirLLM (Execução)
- Executa modelos grandes em hardware limitado
- Suporta compressão 4-bit e 8-bit
- Ideal para GPUs com pouca VRAM

## 📦 Instalação

### Requisitos
- Python 3.9+
- Ollama (opcional) - [ollama.ai](https://ollama.ai)
- LMStudio (opcional) - [lmstudio.ai](https://lmstudio.ai)

### Instalar dependências

```bash
pip install -r requirements.txt
```

### Executar aplicação

```bash
python main.py
```

## 🏗️ Criar Executável (.exe)

```bash
# Instalar PyInstaller
pip install pyinstaller

# Opção 1: Usar script
python build_exe.py

# Opção 2: Usar spec file
pyinstaller AILocalManager.spec

# Opção 3: Comando direto
pyinstaller --name="AILocalManager" --windowed --onefile main.py
```

O executável será criado em `dist/AILocalManager.exe`

## 🚀 Uso

### 1. Configurar Backend
- Vá em **Configurações**
- Escolha **🅰️ Ollama** ou **🅱️ LMStudio**
- Configure as URLs se necessário

### 2. Baixar Modelo
- Vá em **Download de Modelos**
- Selecione um modelo da lista
- Clique em **⬇️ Baixar Modelo**

### 3. Conversar
- Vá em **Chat**
- Selecione o backend de execução
- Escolha o modelo
- Digite sua mensagem e envie!

## 📁 Estrutura do Projeto

```
ai-local-manager/
├── main.py                 # Entrada principal
├── requirements.txt        # Dependências
├── build_exe.py           # Script de build
├── AILocalManager.spec    # Configuração PyInstaller
├── src/
│   ├── ui/
│   │   ├── main_window.py    # Janela principal
│   │   ├── download_tab.py   # Aba de download
│   │   ├── chat_tab.py       # Aba de chat
│   │   └── settings_tab.py   # Aba de configurações
│   ├── backends/
│   │   ├── ollama_backend.py   # Integração Ollama
│   │   ├── lmstudio_backend.py # Integração LMStudio
│   │   └── airllm_backend.py   # Integração AirLLM
│   └── utils/
│       └── config.py          # Gerenciador de configurações
└── assets/                # Recursos (ícones, etc.)
```

## ⚙️ Configuração

As configurações são salvas em:
- **Windows**: `%APPDATA%/AILocalManager/config.json`
- **Linux/Mac**: `~/.config/ailocalmanager/config.json`

## 🤝 Contribuição

Contribuições são bem-vindas! Abra uma issue ou pull request.

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.
