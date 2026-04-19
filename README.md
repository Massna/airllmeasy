# 🤖 AI Local Manager

Desktop application to manage and run AI models locally.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **📥 Model Downloads**: Support for Ollama and LMStudio
- **💬 AI Chat**: Chat with local models
- **🚀 AirLLM**: Run large models with limited memory
- **⚙️ Configurable**: Switch between backends easily
- **🎨 Modern Interface**: Elegant dark theme

## 🔧 Supported Backends

### Option A - Ollama (Download)
- Direct download from the Ollama registry
- Models: Llama, Mistral, CodeLlama, Phi, etc.
- Can run directly OR load into AirLLM

### Option B - LMStudio (Download)
- Download GGUF files from HuggingFace
- Great for quantized models
- Can run directly OR load into AirLLM

### 🚀 AirLLM (Execution)
- **Runs models downloaded by Ollama or LMStudio**
- Supports GGUF models (via llama-cpp-python)
- Supports HuggingFace models with 4-bit/8-bit compression
- Ideal for GPUs with limited VRAM

## 📋 Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                      MODEL DOWNLOAD                          │
├─────────────────────────────────────────────────────────────┤
│  🅰️ Ollama           │  🅱️ LMStudio                         │
│  - llama3.2          │  - GGUF files from HuggingFace       │
│  - mistral           │  - TheBloke/Llama-2-7B-GGUF          │
│  - codellama         │  - bartowski/gemma-2-2b-it-GGUF      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      MODEL EXECUTION                         │
├─────────────────────────────────────────────────────────────┤
│  🅰️ Ollama (native)  │  🅱️ LMStudio (native)  │  🚀 AirLLM │
│  - Fast              │  - OpenAI API          │  - GGUF     │
│  - Optimized         │  - Easy to use         │  - HuggingFace│
│                      │                        │  - 4-bit/8-bit│
└─────────────────────────────────────────────────────────────┘
```

## 📦 Installation

### Requirements
- Python 3.9+
- Ollama (optional) - [ollama.ai](https://ollama.ai)
- LMStudio (optional) - [lmstudio.ai](https://lmstudio.ai)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the application

```bash
python main.py
```

## 🏗️ Build Executable

The build script auto-detects the current OS and produces a standalone binary.

### Windows

```bash
pip install pyinstaller
python build_exe.py
```

Output: `dist/AILocalManager.exe`

### Linux

```bash
# Install system dependencies for Qt (Debian/Ubuntu)
sudo apt-get install -y libegl1 libxkbcommon0 libxcb-cursor0 \
    libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libdbus-1-3

pip install pyinstaller
python build_exe.py
```

Output: `dist/AILocalManager` (+ a `.desktop` launcher file)

To add to your app menu:
```bash
cp dist/AILocalManager.desktop ~/.local/share/applications/
```

### macOS

```bash
pip install pyinstaller
python build_exe.py
```

Output: `dist/AILocalManager`

### Options

```bash
python build_exe.py --console   # Keep terminal visible (debug mode)
```

### Using the spec file directly

```bash
pyinstaller AILocalManager.spec
```

### CI/CD (GitHub Actions)

The project includes a workflow at `.github/workflows/build.yml` that:
- Builds Linux and Windows binaries on every version tag (`v*`)
- Can be triggered manually via the GitHub Actions UI
- Automatically creates a GitHub Release with the binaries attached

## 🚀 Usage

### 1. Configure Backend
- Go to **Settings**
- Choose **🅰️ Ollama** or **🅱️ LMStudio**
- Configure URLs if needed

### 2. Download a Model
- Go to **Model Download**
- Select a model from the list
- Click **⬇️ Download Model**

### 3. Chat
- Go to **Chat**
- Select the execution backend
- Choose the model
- Type your message and send!

## 📁 Project Structure

```
ai-local-manager/
├── main.py                 # Main entry point
├── requirements.txt        # Dependencies
├── build_exe.py           # Build script
├── AILocalManager.spec    # PyInstaller configuration
├── src/
│   ├── ui/
│   │   ├── main_window.py    # Main window
│   │   ├── download_tab.py   # Download tab
│   │   ├── chat_tab.py       # Chat tab
│   │   └── settings_tab.py   # Settings tab
│   ├── backends/
│   │   ├── ollama_backend.py   # Ollama integration
│   │   ├── lmstudio_backend.py # LMStudio integration
│   │   └── airllm_backend.py   # AirLLM integration
│   └── utils/
│       └── config.py          # Configuration manager
└── assets/                # Resources (icons, etc.)
```

## ⚙️ Configuration

Settings are saved at:
- **Windows**: `%APPDATA%/AILocalManager/config.json`
- **Linux/Mac**: `~/.config/ailocalmanager/config.json`

### Locating the AirLLM Package

If the application shows that **AirLLM is not installed** or fails to import the package, even after `pip install airllm`, this usually happens when the app runs with a **different Python** than the one you used in the terminal (e.g., packaged executable or IDE pointing to another interpreter).

1. Open **Settings** in the app.
2. In the **AirLLM** section, use **Browse…** and select one of these folders:
   - The **`site-packages`** folder of the environment where `airllm` was installed, for example:
     - Windows: `...\venv\Lib\site-packages`
     - Linux/macOS: `.../lib/python3.x/site-packages`
   - Or the **virtual environment root** (`venv`): the app tries to locate `site-packages` automatically.
3. Confirm that the status line below the field indicates an **`airllm`** subfolder was found.
4. Click **Save Settings** and use **Check System Requirements** to test again.

**How to find the path in the terminal** (use the same Python you intend to run the app with):

```bash
pip show airllm
```

The **Location** field points to the correct `site-packages` folder. You can also use:

```bash
python -c "import site; print(site.getsitepackages())"
```

The **Clear** option removes the extra path and reverts to using only the default `sys.path` of the process running the application.

**Editable installation** (`pip install -e path/to/repo`): the `airllm` code may not be inside `site-packages` as a folder, but rather in another directory referenced by a **`.pth`** file in that folder. The interpreter only reads `.pth` files at Python startup; this app reads those files manually when configuring the path. Therefore, even with `-e` installation, point to the correct **`site-packages`** folder of the environment — it's not enough to point only to the `airllm` source code folder if the import depends on pip's layout.

If it still fails, use **Check System Requirements**: the message shows the **exact error** from `import` (missing dependency, DLL, etc.), not just "not installed".

### Error: `No module named 'optimum.bettertransformer'`

This appears when the installed **optimum** is the **2.x** series: the `bettertransformer` module was removed, but **AirLLM** still depends on it. This is not a path configuration issue.

In the same Python environment as the app, install compatible versions (as in the project's `requirements.txt`):

```bash
pip install "optimum>=1.17,<2" "transformers>=4.40,<4.49"
```

If you already have versions that are too new, you can force:

```bash
pip install "optimum==1.17.0" "transformers==4.48.0"
```

Then run **Check System Requirements** again.

## 🤝 Contributing

Contributions are welcome! Open an issue or pull request.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
