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

### Opção A - Ollama (Download)
- Download direto do registro Ollama
- Modelos: Llama, Mistral, CodeLlama, Phi, etc.
- Pode executar diretamente OU carregar no AirLLM

### Opção B - LMStudio (Download)
- Download de arquivos GGUF do HuggingFace
- Ótimo para modelos quantizados
- Pode executar diretamente OU carregar no AirLLM

### 🚀 AirLLM (Execução)
- **Executa modelos baixados pelo Ollama ou LMStudio**
- Suporta modelos GGUF (via llama-cpp-python)
- Suporta modelos HuggingFace com compressão 4-bit/8-bit
- Ideal para GPUs com pouca VRAM

## 📋 Fluxo de Trabalho

```
┌─────────────────────────────────────────────────────────────┐
│                    DOWNLOAD DE MODELOS                       │
├─────────────────────────────────────────────────────────────┤
│  🅰️ Ollama          │  🅱️ LMStudio                          │
│  - llama3.2         │  - Arquivos GGUF do HuggingFace       │
│  - mistral          │  - TheBloke/Llama-2-7B-GGUF          │
│  - codellama        │  - bartowski/gemma-2-2b-it-GGUF      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXECUÇÃO DE MODELOS                       │
├─────────────────────────────────────────────────────────────┤
│  🅰️ Ollama (nativo) │  🅱️ LMStudio (nativo)  │  🚀 AirLLM  │
│  - Rápido           │  - API OpenAI          │  - GGUF     │
│  - Otimizado        │  - Fácil de usar       │  - HuggingFace│
│                     │                        │  - 4-bit/8-bit│
└─────────────────────────────────────────────────────────────┘
```

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

### Localizar o pacote AirLLM nos arquivos

Se o aplicativo mostrar que o **AirLLM não está instalado** ou falhar ao importar o pacote, mesmo depois de `pip install airllm`, isso costuma acontecer quando o app roda com **outro Python** do que o que você usou no terminal (por exemplo, executável empacotado ou IDE apontando para outro interpretador).

1. Abra **Configurações** no app.
2. Na seção **AirLLM**, use **Procurar…** e selecione uma destas pastas:
   - A pasta **`site-packages`** do ambiente onde o `airllm` foi instalado, por exemplo:
     - Windows: `...\venv\Lib\site-packages`
     - Linux/macOS: `.../lib/python3.x/site-packages`
   - Ou a **raiz do ambiente virtual** (`venv`): o app tenta localizar `site-packages` automaticamente.
3. Confirme se a linha de status abaixo do campo indica que foi encontrada uma subpasta **`airllm`**.
4. Clique em **Salvar Configurações** e use **Verificar Requisitos do Sistema** para testar de novo.

**Como descobrir o caminho no terminal** (use o mesmo Python com que você pretende rodar o app):

```bash
pip show airllm
```

O campo **Location** aponta para a pasta `site-packages` correta. Você também pode usar:

```bash
python -c "import site; print(site.getsitepackages())"
```

A opção **Limpar** remove o caminho extra e volta a usar apenas o `sys.path` padrão do processo que executa o aplicativo.

## 🤝 Contribuição

Contribuições são bem-vindas! Abra uma issue ou pull request.

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.
