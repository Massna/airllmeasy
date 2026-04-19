"""Chat tab with AI models."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QPlainTextEdit, QComboBox, QGroupBox, QSplitter,
    QFrame, QSpinBox, QDoubleSpinBox, QMessageBox, QRadioButton,
    QButtonGroup, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QTextCursor

from ..utils.config import Config
from ..backends.ollama_backend import OllamaBackend
from ..backends.lmstudio_backend import LMStudioBackend
from ..backends.airllm_backend import AirLLMBackend
from .install_dialog import prompt_install_airllm, prompt_install_llama_cpp


class ChatWorker(QThread):
    """Worker thread for chat."""
    token_received = Signal(str)
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, backend, model, message, max_tokens=256, temperature=0.7):
        super().__init__()
        self.backend = backend
        self.model = model
        self.message = message
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.backend_type = None
    
    def run(self):
        try:
            if isinstance(self.backend, OllamaBackend):
                response = self.backend.chat(
                    self.model,
                    self.message,
                    stream_callback=lambda t: self.token_received.emit(t)
                )
            elif isinstance(self.backend, LMStudioBackend):
                response = self.backend.chat(
                    self.model,
                    self.message,
                    stream_callback=lambda t: self.token_received.emit(t)
                )
            elif isinstance(self.backend, AirLLMBackend):
                response = self.backend.chat(
                    self.message,
                    max_new_tokens=self.max_tokens,
                    stream_callback=lambda t: self.token_received.emit(t)
                )
            else:
                response = "Backend not supported"
            
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))


class LoadModelWorker(QThread):
    """Worker thread for loading a model in AirLLM."""
    progress = Signal(str)
    finished = Signal(bool, str)
    missing_package = Signal(str)  # emits AirLLMBackend.MISSING_AIRLLM or MISSING_LLAMACPP
    
    def __init__(self, airllm: AirLLMBackend, model_path: str, compression: str, model_type: str = "huggingface"):
        super().__init__()
        self.airllm = airllm
        self.model_path = model_path
        self.compression = compression
        self.model_type = model_type
    
    def run(self):
        try:
            success = self.airllm.load_model(
                self.model_path,
                progress_callback=lambda s: self.progress.emit(s),
                compression=self.compression,
                model_type=self.model_type
            )
            if success:
                self.finished.emit(True, "Model loaded!")
            else:
                self.finished.emit(False, "Failed to load model")
        except ImportError as exc:
            marker = str(exc)
            self.missing_package.emit(marker)
            self.finished.emit(False, f"Package not found: {marker}")


class ModelSelectorDialog(QDialog):
    """Dialog for selecting a model for AirLLM."""
    
    def __init__(self, airllm: AirLLMBackend, parent=None):
        super().__init__(parent)
        self.airllm = airllm
        self.selected_model = None
        self.selected_type = None
        
        self.setWindowTitle("Select Model for AirLLM")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self._load_models()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        info_label = QLabel(
            "Select a model downloaded by Ollama or LMStudio to run with AirLLM:"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Model list
        self.model_list = QListWidget()
        self.model_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.model_list)

        refresh_row = QHBoxLayout()
        self.airllm_list_refresh_btn = QPushButton("🔄 Refresh list")
        self.airllm_list_refresh_btn.setToolTip(
            "Ollama: uses the API (service must be running). LM Studio: scans model folders."
        )
        self.airllm_list_refresh_btn.clicked.connect(self._load_models)
        refresh_row.addWidget(self.airllm_list_refresh_btn)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)
        
        # Or type manually
        layout.addWidget(QLabel("Or type a HuggingFace model:"))
        self.hf_input = QComboBox()
        self.hf_input.setEditable(True)
        # Add popular models
        for model in AirLLMBackend.get_supported_models():
            self.hf_input.addItem(f"{model['name']} ({model['size']})", model['name'])
        layout.addWidget(self.hf_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_models(self):
        """Load the list of available models."""
        self.model_list.clear()
        
        # Ollama models
        ollama_models = self.airllm.list_ollama_models()
        if ollama_models:
            header = QListWidgetItem("📦 Ollama Models:")
            header.setFlags(Qt.NoItemFlags)
            self.model_list.addItem(header)
            
            for model in ollama_models:
                item = QListWidgetItem(f"  🦙 {model['name']}")
                item.setData(Qt.UserRole, model)
                self.model_list.addItem(item)
        
        # LMStudio models (GGUF)
        lmstudio_models = self.airllm.list_lmstudio_models()
        if lmstudio_models:
            header = QListWidgetItem("📦 LMStudio Models (GGUF):")
            header.setFlags(Qt.NoItemFlags)
            self.model_list.addItem(header)
            
            for model in lmstudio_models:
                size_mb = model.get('size', 0) / (1024*1024)
                item = QListWidgetItem(f"  📄 {model['name']} ({size_mb:.0f} MB)")
                item.setData(Qt.UserRole, model)
                self.model_list.addItem(item)
        
        if not ollama_models and not lmstudio_models:
            item = QListWidgetItem("No local models found")
            item.setFlags(Qt.NoItemFlags)
            self.model_list.addItem(item)
    
    def get_selection(self):
        """Returns the selected model and its type."""
        # Check if selected from list
        current = self.model_list.currentItem()
        if current:
            model_data = current.data(Qt.UserRole)
            if model_data:
                return model_data.get('path', model_data.get('name')), model_data.get('type', 'huggingface')
        
        # Check if typed manually
        hf_text = self.hf_input.currentText().strip()
        if hf_text:
            # Remove size if present
            if " (" in hf_text:
                hf_text = hf_text.split(" (")[0]
            return hf_text, "huggingface"
        
        return None, None


class ChatTab(QWidget):
    """Chat tab with AI models."""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        # Backends
        self.ollama = OllamaBackend(config.ollama_url)
        self.lmstudio = LMStudioBackend(config.lmstudio_url)
        self.airllm = AirLLMBackend(config)
        
        self.chat_worker = None
        self.load_worker = None
        self.conversation_history = []
        
        self._setup_ui()
        self._refresh_models()
    
    def _setup_ui(self):
        """Set up the chat tab interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === Chat Settings ===
        config_frame = QFrame()
        config_layout = QHBoxLayout(config_frame)
        config_layout.setContentsMargins(0, 0, 0, 0)
        
        # Execution backend selector
        config_layout.addWidget(QLabel("Run with:"))
        
        self.exec_backend_group = QButtonGroup(self)
        
        self.ollama_radio = QRadioButton("🅰️ Ollama")
        self.ollama_radio.setChecked(True)
        self.exec_backend_group.addButton(self.ollama_radio)
        config_layout.addWidget(self.ollama_radio)
        
        self.lmstudio_radio = QRadioButton("🅱️ LMStudio")
        self.exec_backend_group.addButton(self.lmstudio_radio)
        config_layout.addWidget(self.lmstudio_radio)
        
        self.airllm_radio = QRadioButton("🚀 AirLLM")
        self.exec_backend_group.addButton(self.airllm_radio)
        config_layout.addWidget(self.airllm_radio)
        
        self.exec_backend_group.buttonClicked.connect(self._on_exec_backend_changed)
        
        config_layout.addSpacing(20)
        
        # Model selector
        config_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        config_layout.addWidget(self.model_combo)
        
        self.refresh_models_btn = QPushButton("🔄")
        self.refresh_models_btn.setMaximumWidth(40)
        self.refresh_models_btn.clicked.connect(self._refresh_models)
        config_layout.addWidget(self.refresh_models_btn)
        
        config_layout.addStretch()
        
        # Load button (for AirLLM)
        self.load_model_btn = QPushButton("📂 Load Model")
        self.load_model_btn.setVisible(False)
        self.load_model_btn.clicked.connect(self._load_airllm_model)
        config_layout.addWidget(self.load_model_btn)
        
        layout.addWidget(config_frame)
        
        # === Chat Area ===
        chat_splitter = QSplitter(Qt.Vertical)
        
        # Conversation history
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(300)
        font = QFont("Consolas", 11)
        self.chat_display.setFont(font)
        chat_splitter.addWidget(self.chat_display)
        
        # Input area
        input_frame = QFrame()
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_text = QPlainTextEdit()
        self.input_text.setMaximumHeight(100)
        self.input_text.setPlaceholderText("Type your message here...")
        self.input_text.setFont(font)
        input_layout.addWidget(self.input_text)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        # Parameters
        buttons_layout.addWidget(QLabel("Tokens:"))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(1, 4096)
        self.tokens_spin.setValue(self.config.max_tokens)
        self.tokens_spin.setMaximumWidth(80)
        buttons_layout.addWidget(self.tokens_spin)
        
        buttons_layout.addWidget(QLabel("Temp:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(self.config.temperature)
        self.temp_spin.setMaximumWidth(70)
        buttons_layout.addWidget(self.temp_spin)
        
        buttons_layout.addStretch()
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self._clear_chat)
        buttons_layout.addWidget(self.clear_btn)
        
        self.send_btn = QPushButton("📤 Send")
        self.send_btn.setMinimumWidth(100)
        self.send_btn.clicked.connect(self._send_message)
        buttons_layout.addWidget(self.send_btn)
        
        input_layout.addLayout(buttons_layout)
        
        chat_splitter.addWidget(input_frame)
        chat_splitter.setSizes([400, 150])
        
        layout.addWidget(chat_splitter)
        
        # Status
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # Welcome message
        self._add_system_message("Welcome to AI Local Manager! Select a model and start chatting.")
    
    def _on_exec_backend_changed(self, button):
        """When the execution backend changes."""
        is_airllm = button == self.airllm_radio
        self.load_model_btn.setVisible(is_airllm)
        self.model_combo.setVisible(not is_airllm)
        self.refresh_models_btn.setVisible(not is_airllm)
        
        if not is_airllm:
            self._refresh_models()
        else:
            self._update_airllm_status()
    
    def _update_airllm_status(self):
        """Update AirLLM status."""
        if self.airllm.is_model_loaded():
            model_name = self.airllm.get_loaded_model_name()
            self.status_label.setText(f"✅ AirLLM: {model_name} loaded")
            self.status_label.setStyleSheet("color: #a6e3a1;")
        else:
            self.status_label.setText("ℹ️ AirLLM: No model loaded")
            self.status_label.setStyleSheet("color: #fab387;")
    
    def _refresh_models(self):
        """Refresh the list of available models."""
        self.model_combo.clear()
        
        if self.ollama_radio.isChecked():
            if self.ollama.is_running():
                models = self.ollama.list_models()
                for model in models:
                    self.model_combo.addItem(model.get("name", ""))
                self.status_label.setText("✅ Connected to Ollama")
                self.status_label.setStyleSheet("color: #a6e3a1;")
            else:
                self.status_label.setText("❌ Ollama is not running")
                self.status_label.setStyleSheet("color: #f38ba8;")
        
        elif self.lmstudio_radio.isChecked():
            if self.lmstudio.is_running():
                models = self.lmstudio.list_models()
                for model in models:
                    self.model_combo.addItem(model.get("name", ""))
                self.status_label.setText("✅ Connected to LMStudio")
                self.status_label.setStyleSheet("color: #a6e3a1;")
            else:
                self.status_label.setText("❌ LMStudio server is not running")
                self.status_label.setStyleSheet("color: #f38ba8;")
        
        if self.model_combo.count() == 0 and not self.airllm_radio.isChecked():
            self.model_combo.addItem("No models available")
    
    def _load_airllm_model(self):
        """Load a model in AirLLM."""
        # Show model selection dialog
        dialog = ModelSelectorDialog(self.airllm, self)
        
        if dialog.exec() == QDialog.Accepted:
            model_path, model_type = dialog.get_selection()
            
            if not model_path:
                QMessageBox.warning(self, "Warning", "No model selected!")
                return
            
            self._start_model_load(model_path, model_type)

    def _start_model_load(self, model_path: str, model_type: str):
        """Start loading the model (can be called after installation)."""
        self.load_model_btn.setEnabled(False)
        self.status_label.setText(f"Loading {model_path}...")

        # Save for possible retry after installation
        self._pending_model_path = model_path
        self._pending_model_type = model_type
        
        self.load_worker = LoadModelWorker(
            self.airllm,
            model_path,
            self.config.airllm_compression,
            model_type
        )
        self.load_worker.progress.connect(lambda s: self.status_label.setText(s))
        self.load_worker.missing_package.connect(self._on_missing_package)
        self.load_worker.finished.connect(self._on_model_loaded)
        self.load_worker.start()

    def _on_missing_package(self, marker: str):
        """Called when a required package is not installed.
        
        Shows an installation dialog with progress bar and,
        if the user installs successfully, retries loading the model.
        """
        installed = False
        if marker == AirLLMBackend.MISSING_AIRLLM:
            installed = prompt_install_airllm(parent=self)
        elif marker == AirLLMBackend.MISSING_LLAMACPP:
            installed = prompt_install_llama_cpp(parent=self)
        else:
            QMessageBox.warning(
                self, "Missing Package",
                f"Required package not found: {marker}\n\n"
                "Install manually via pip and try again."
            )
            return

        if installed:
            # Retry loading the model after successful installation
            self._add_system_message("✅ Package installed! Trying to load the model again…")
            self._start_model_load(self._pending_model_path, self._pending_model_type)
    
    def _on_model_loaded(self, success: bool, message: str):
        """Callback when AirLLM model is loaded."""
        self.load_model_btn.setEnabled(True)
        
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: #a6e3a1;")
            self._add_system_message(f"Model loaded: {self.airllm.get_loaded_model_name()}")
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: #f38ba8;")
    
    def _send_message(self):
        """Send a message to the model."""
        message = self.input_text.toPlainText().strip()
        if not message:
            return
        
        if self.chat_worker and self.chat_worker.isRunning():
            QMessageBox.warning(self, "Warning", "Wait for the previous response!")
            return
        
        # Determine backend
        if self.ollama_radio.isChecked():
            backend = self.ollama
            model = self.model_combo.currentText()
            if not self.ollama.is_running():
                QMessageBox.warning(self, "Error", "Ollama is not running!")
                return
        elif self.lmstudio_radio.isChecked():
            backend = self.lmstudio
            model = self.model_combo.currentText()
            if not self.lmstudio.is_running():
                QMessageBox.warning(self, "Error", "LMStudio is not running!")
                return
        else:  # AirLLM
            backend = self.airllm
            model = None
            if not self.airllm.is_model_loaded():
                QMessageBox.warning(self, "Error", "Load a model first!")
                return
        
        # Add user message to chat
        self._add_user_message(message)
        self.input_text.clear()
        
        # Prepare assistant response
        self._add_assistant_header()
        
        # Start worker
        self.chat_worker = ChatWorker(
            backend, model, message,
            max_tokens=self.tokens_spin.value(),
            temperature=self.temp_spin.value()
        )
        self.chat_worker.token_received.connect(self._on_token_received)
        self.chat_worker.finished.connect(self._on_chat_finished)
        self.chat_worker.error.connect(self._on_chat_error)
        
        self.send_btn.setEnabled(False)
        self.chat_worker.start()
    
    def _add_system_message(self, message: str):
        """Add a system message."""
        self.chat_display.append(
            f'<p style="color: #a6adc8; font-style: italic;">📋 {message}</p>'
        )
    
    def _add_user_message(self, message: str):
        """Add a user message."""
        self.chat_display.append(
            f'<p style="color: #89b4fa;"><b>👤 You:</b></p>'
            f'<p style="margin-left: 20px;">{message}</p>'
        )
        self.conversation_history.append({"role": "user", "content": message})
    
    def _add_assistant_header(self):
        """Add assistant response header."""
        self.chat_display.append(
            f'<p style="color: #a6e3a1;"><b>🤖 Assistant:</b></p>'
            f'<p style="margin-left: 20px;">'
        )
    
    def _on_token_received(self, token: str):
        """Callback for each received token (streaming)."""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(token)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
    
    def _on_chat_finished(self, response: str):
        """Callback when chat finishes."""
        self.chat_display.append("</p><br>")
        self.send_btn.setEnabled(True)
        self.conversation_history.append({"role": "assistant", "content": response})
    
    def _on_chat_error(self, error: str):
        """Callback for chat error."""
        self.chat_display.append(
            f'<p style="color: #f38ba8;">❌ Error: {error}</p>'
        )
        self.send_btn.setEnabled(True)
    
    def _clear_chat(self):
        """Clear the chat history."""
        self.chat_display.clear()
        self.conversation_history.clear()
        self._add_system_message("Chat cleared. Start a new conversation!")
