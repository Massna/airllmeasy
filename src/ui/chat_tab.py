"""Chat tab with AI models — premium design with file operations support."""
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QPlainTextEdit, QComboBox, QGroupBox, QSplitter,
    QFrame, QSpinBox, QDoubleSpinBox, QMessageBox, QRadioButton,
    QButtonGroup, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox,
    QFileDialog, QCheckBox, QScrollArea, QSizePolicy, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor, QColor, QAction

from ..utils.config import Config
from ..utils.file_ops import WorkspaceManager
from ..utils.extensions import ExtensionManager
from ..backends.ollama_backend import OllamaBackend
from ..backends.lmstudio_backend import LMStudioBackend
from ..backends.airllm_backend import AirLLMBackend
from .install_dialog import prompt_install_airllm, prompt_install_llama_cpp


class ChatWorker(QThread):
    """Worker thread for chat."""
    token_received = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, backend, model, message, system_prompt="", max_tokens=256, temperature=0.7, conversation_history=None):
        super().__init__()
        self.backend = backend
        self.model = model
        self.message = message
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.conversation_history = conversation_history or []

    def run(self):
        try:
            if isinstance(self.backend, OllamaBackend):
                response = self.backend.chat(
                    self.model,
                    self.message,
                    system_prompt=self.system_prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    stream_callback=lambda t: self.token_received.emit(t),
                    conversation_history=self.conversation_history
                )
            elif isinstance(self.backend, LMStudioBackend):
                response = self.backend.chat(
                    self.model,
                    self.message,
                    system_prompt=self.system_prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    stream_callback=lambda t: self.token_received.emit(t),
                    conversation_history=self.conversation_history
                )
            elif isinstance(self.backend, AirLLMBackend):
                response = self.backend.chat(
                    self.message,
                    system_prompt=self.system_prompt,
                    max_new_tokens=self.max_tokens,
                    stream_callback=lambda t: self.token_received.emit(t),
                    conversation_history=self.conversation_history
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
    missing_package = Signal(str)

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
    """Dialog for selecting a model for AirLLM — redesigned."""

    def __init__(self, airllm: AirLLMBackend, parent=None):
        super().__init__(parent)
        self.airllm = airllm
        self.selected_model = None
        self.selected_type = None

        self.setWindowTitle("Select Model for AirLLM")
        self.setMinimumSize(550, 460)
        self._setup_ui()
        self._load_models()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("🚀 Select a model to run with AirLLM")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)

        desc = QLabel(
            "Choose a model downloaded by Ollama or LMStudio, or type a HuggingFace model ID."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6c7086; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(desc)

        # Model list
        self.model_list = QListWidget()
        self.model_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.model_list)

        refresh_row = QHBoxLayout()
        self.airllm_list_refresh_btn = QPushButton("🔄 Refresh")
        self.airllm_list_refresh_btn.setObjectName("GhostBtn")
        self.airllm_list_refresh_btn.setToolTip(
            "Ollama: uses the API (service must be running). LM Studio: scans model folders."
        )
        self.airllm_list_refresh_btn.clicked.connect(self._load_models)
        refresh_row.addWidget(self.airllm_list_refresh_btn)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)

        # HuggingFace input
        hf_label = QLabel("Or type a HuggingFace model:")
        hf_label.setStyleSheet("color: #b4befe; font-weight: bold; font-size: 12px;")
        layout.addWidget(hf_label)

        self.hf_input = QComboBox()
        self.hf_input.setEditable(True)
        for model in AirLLMBackend.get_supported_models():
            self.hf_input.addItem(f"{model['name']} ({model['size']})", model['name'])
        layout.addWidget(self.hf_input)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_models(self):
        """Load the list of available models."""
        self.model_list.clear()

        ollama_models = self.airllm.list_ollama_models()
        if ollama_models:
            header = QListWidgetItem("📦  Ollama Models")
            header.setFlags(Qt.NoItemFlags)
            header.setForeground(QColor("#89b4fa"))
            self.model_list.addItem(header)
            for model in ollama_models:
                item = QListWidgetItem(f"   🦙  {model['name']}")
                item.setData(Qt.UserRole, model)
                self.model_list.addItem(item)

        lmstudio_models = self.airllm.list_lmstudio_models()
        if lmstudio_models:
            header = QListWidgetItem("📦  LMStudio Models (GGUF)")
            header.setFlags(Qt.NoItemFlags)
            header.setForeground(QColor("#b4befe"))
            self.model_list.addItem(header)
            for model in lmstudio_models:
                size_mb = model.get('size', 0) / (1024 * 1024)
                item = QListWidgetItem(f"   📄  {model['name']} ({size_mb:.0f} MB)")
                item.setData(Qt.UserRole, model)
                self.model_list.addItem(item)

        if not ollama_models and not lmstudio_models:
            item = QListWidgetItem("   No local models found")
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(QColor("#6c7086"))
            self.model_list.addItem(item)

    def get_selection(self):
        current = self.model_list.currentItem()
        if current:
            model_data = current.data(Qt.UserRole)
            if model_data:
                return model_data.get('path', model_data.get('name')), model_data.get('type', 'huggingface')

        hf_text = self.hf_input.currentText().strip()
        if hf_text:
            if " (" in hf_text:
                hf_text = hf_text.split(" (")[0]
            return hf_text, "huggingface"

        return None, None


# ─────────────────────────── Workspace Panel ──────────────────────────────────

class WorkspacePanel(QFrame):
    """Panel for managing workspace folders for AI file operations."""

    folders_changed = Signal()

    def __init__(self, config: Config, workspace_mgr: WorkspaceManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.workspace_mgr = workspace_mgr
        self.setObjectName("Card")
        self._setup_ui()
        self._load_folders()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header row
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 18px;")
        header_row.addWidget(icon_label)

        title = QLabel("Workspace")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #b4befe;")
        header_row.addWidget(title)
        header_row.addStretch()

        self.remove_btn = QPushButton("🗑️")
        self.remove_btn.setObjectName("DangerBtn")
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setToolTip("Remove selected item")
        self.remove_btn.setStyleSheet("padding: 2px;")
        self.remove_btn.clicked.connect(self._remove_folder)
        header_row.addWidget(self.remove_btn)
        
        layout.addLayout(header_row)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 0, 0, 4)

        self.add_file_btn = QPushButton("📄 Add File")
        self.add_file_btn.setObjectName("GhostBtn")
        self.add_file_btn.setFixedHeight(28)
        self.add_file_btn.setToolTip("Add specific file")
        self.add_file_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.add_file_btn.clicked.connect(self._add_file)
        btn_row.addWidget(self.add_file_btn)

        self.add_folder_btn = QPushButton("📂 Add Folder")
        self.add_folder_btn.setObjectName("GhostBtn")
        self.add_folder_btn.setFixedHeight(28)
        self.add_folder_btn.setToolTip("Add workspace folder")
        self.add_folder_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.add_folder_btn.clicked.connect(self._add_folder)
        btn_row.addWidget(self.add_folder_btn)

        layout.addLayout(btn_row)

        # Folder list
        self.folder_list = QListWidget()
        self.folder_list.setMaximumHeight(120)
        self.folder_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_list.customContextMenuRequested.connect(self._show_folder_context_menu)
        self.folder_list.setStyleSheet("""
            QListWidget {
                font-size: 11px;
                background-color: rgba(15,15,23,0.6);
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 4px 8px;
            }
        """)
        layout.addWidget(self.folder_list)

        self.file_ops_check = QCheckBox("Enable AI file operations")
        self.file_ops_check.setChecked(self.config.file_ops_enabled)
        self.file_ops_check.setStyleSheet("font-size: 11px; color: #6c7086;")
        self.file_ops_check.toggled.connect(self._on_file_ops_toggled)
        layout.addWidget(self.file_ops_check)

    def _load_folders(self):
        self.folder_list.clear()
        from pathlib import Path
        
        # Ensure manager is in sync by clearing and rebuilding
        self.workspace_mgr.clear_folders()
        
        for folder in self.config.workspace_folders:
            if self.workspace_mgr.add_folder(folder):
                p = Path(folder)
                # Show short name
                parts = folder.replace("\\", "/").split("/")
                short = "/".join(parts[-2:]) if len(parts) > 2 else folder
                icon = "📄" if p.is_file() else "📂"
                item = QListWidgetItem(f"{icon} {short}")
                item.setData(Qt.UserRole, folder)
                item.setToolTip(folder)
                self.folder_list.addItem(item)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select workspace folder")
        if folder:
            if self.workspace_mgr.add_folder(folder):
                folders = self.config.workspace_folders
                if folder not in folders:
                    folders.append(folder)
                    self.config.workspace_folders = folders
                    self.config.save()
                self._load_folders()
                self.folders_changed.emit()

    def _add_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select workspace files", "", "All Files (*)")
        if files:
            added = False
            folders = self.config.workspace_folders
            for f in files:
                if self.workspace_mgr.add_folder(f):
                    if f not in folders:
                        folders.append(f)
                        added = True
            if added:
                self.config.workspace_folders = folders
                self.config.save()
                self._load_folders()
                self.folders_changed.emit()

    def _show_folder_context_menu(self, pos):
        item = self.folder_list.itemAt(pos)
        if item:
            menu = QMenu(self)
            remove_action = QAction("🗑️ Remove", self)
            remove_action.triggered.connect(lambda: self._remove_specific_folder(item))
            menu.addAction(remove_action)
            menu.exec(self.folder_list.mapToGlobal(pos))

    def _remove_specific_folder(self, item):
        folder = item.data(Qt.UserRole)
        self.workspace_mgr.remove_folder(folder)
        folders = self.config.workspace_folders
        if folder in folders:
            folders.remove(folder)
            self.config.workspace_folders = folders
            self.config.save()
        self._load_folders()
        self.folders_changed.emit()

    def _remove_folder(self):
        current = self.folder_list.currentItem()
        if current:
            self._remove_specific_folder(current)

    def _on_file_ops_toggled(self, checked):
        self.config.file_ops_enabled = checked
        self.config.save()


# ─────────────────────────────── Chat Tab ─────────────────────────────────────

class ChatTab(QWidget):
    """Chat tab with AI models — premium design with file operations."""

    def __init__(self, config: Config, extension_mgr):
        super().__init__()
        self.config = config

        # Backends
        self.ollama = OllamaBackend(config.ollama_url)
        self.lmstudio = LMStudioBackend(config.lmstudio_url)
        self.airllm = AirLLMBackend(config)

        # Workspace manager for file operations
        self.workspace_mgr = WorkspaceManager(config.workspace_folders)
        self.extension_mgr = extension_mgr

        self.chat_worker = None
        self.load_worker = None
        self.conversation_history = []

        self._setup_ui()
        self._load_sessions()
        self._refresh_models()

    def _setup_ui(self):
        """Set up the chat tab interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Left: Main chat area ──
        chat_area = QWidget()
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(10)

        # === Session Row ===
        session_frame = QFrame()
        session_frame.setObjectName("Card")
        session_layout = QHBoxLayout(session_frame)
        session_layout.setContentsMargins(14, 8, 14, 8)
        
        session_label = QLabel("Session:")
        session_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        session_layout.addWidget(session_label)
        
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(200)
        self.session_combo.currentIndexChanged.connect(self._on_session_changed)
        session_layout.addWidget(self.session_combo)
        
        self.new_session_btn = QPushButton("➕ New")
        self.new_session_btn.setObjectName("SuccessBtn")
        self.new_session_btn.clicked.connect(self._create_new_session)
        session_layout.addWidget(self.new_session_btn)
        
        self.del_session_btn = QPushButton("🗑️")
        self.del_session_btn.setObjectName("DangerBtn")
        self.del_session_btn.clicked.connect(self._delete_session)
        session_layout.addWidget(self.del_session_btn)
        
        session_layout.addStretch()
        chat_layout.addWidget(session_frame)

        # === Backend selector row ===
        config_frame = QFrame()
        config_frame.setObjectName("Card")
        config_layout = QHBoxLayout(config_frame)
        config_layout.setContentsMargins(14, 10, 14, 10)
        config_layout.setSpacing(12)

        run_label = QLabel("Run with:")
        run_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        config_layout.addWidget(run_label)

        self.exec_backend_group = QButtonGroup(self)

        self.ollama_radio = QRadioButton("Ollama")
        self.ollama_radio.setChecked(True)
        self.exec_backend_group.addButton(self.ollama_radio)
        config_layout.addWidget(self.ollama_radio)

        self.lmstudio_radio = QRadioButton("LMStudio")
        self.exec_backend_group.addButton(self.lmstudio_radio)
        config_layout.addWidget(self.lmstudio_radio)

        self.airllm_radio = QRadioButton("AirLLM")
        self.exec_backend_group.addButton(self.airllm_radio)
        config_layout.addWidget(self.airllm_radio)

        self.exec_backend_group.buttonClicked.connect(self._on_exec_backend_changed)

        # Divider
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setFixedHeight(24)
        divider.setStyleSheet("background-color: rgba(255,255,255,0.08);")
        config_layout.addWidget(divider)

        # Model selector
        model_label = QLabel("Model:")
        model_label.setStyleSheet("color: #6c7086; font-size: 12px;")
        config_layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        config_layout.addWidget(self.model_combo)

        self.refresh_models_btn = QPushButton("↻ Refresh")
        self.refresh_models_btn.setObjectName("GhostBtn")
        self.refresh_models_btn.setFixedHeight(32)
        self.refresh_models_btn.clicked.connect(self._refresh_models)
        config_layout.addWidget(self.refresh_models_btn)

        config_layout.addStretch()

        # Load button (for AirLLM)
        self.load_model_btn = QPushButton("📂 Load")
        self.load_model_btn.setObjectName("SuccessBtn")
        self.load_model_btn.setVisible(False)
        self.load_model_btn.clicked.connect(self._load_airllm_model)
        config_layout.addWidget(self.load_model_btn)

        chat_layout.addWidget(config_frame)

        # === Chat display ===
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(300)
        chat_font = QFont("Consolas", 11)
        self.chat_display.setFont(chat_font)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: rgba(12,12,20,0.8);
                border: 1px solid rgba(255,255,255,0.04);
                border-radius: 14px;
                padding: 16px;
            }
        """)
        chat_layout.addWidget(self.chat_display, stretch=1)

        # === Input area ===
        input_frame = QFrame()
        input_frame.setObjectName("Card")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(14, 12, 14, 12)
        input_layout.setSpacing(8)

        self.input_text = QPlainTextEdit()
        self.input_text.setMaximumHeight(90)
        self.input_text.setPlaceholderText("Type your message here… (Enter to send, Shift+Enter for new line)")
        self.input_text.setFont(chat_font)
        self.input_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: rgba(15,15,23,0.6);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
                padding: 10px;
            }
            QPlainTextEdit:focus {
                border-color: rgba(139,180,250,0.3);
            }
        """)
        input_layout.addWidget(self.input_text)

        # Buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Parameters
        tokens_label = QLabel("Tokens:")
        tokens_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        buttons_layout.addWidget(tokens_label)

        spinbox_css = """
            QSpinBox, QDoubleSpinBox {
                background-color: rgba(15,15,23,0.8);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                padding: 4px;
                color: #e0e0ec;
            }
        """

        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(1, 4096)
        self.tokens_spin.setValue(self.config.max_tokens)
        self.tokens_spin.setFixedWidth(85)
        self.tokens_spin.setFixedHeight(30)
        self.tokens_spin.setStyleSheet(spinbox_css)
        buttons_layout.addWidget(self.tokens_spin)

        temp_label = QLabel("Temp:")
        temp_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        buttons_layout.addWidget(temp_label)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(self.config.temperature)
        self.temp_spin.setFixedWidth(75)
        self.temp_spin.setFixedHeight(30)
        self.temp_spin.setStyleSheet(spinbox_css)
        buttons_layout.addWidget(self.temp_spin)

        buttons_layout.addStretch()

        self.clear_btn = QPushButton("🗑 Clear")
        self.clear_btn.setObjectName("GhostBtn")
        self.clear_btn.setFixedHeight(34)
        self.clear_btn.clicked.connect(self._clear_chat)
        buttons_layout.addWidget(self.clear_btn)

        self.send_btn = QPushButton("Send 🚀")
        self.send_btn.setMinimumWidth(100)
        self.send_btn.setFixedHeight(36)
        self.send_btn.clicked.connect(self._send_message)
        buttons_layout.addWidget(self.send_btn)

        input_layout.addLayout(buttons_layout)

        chat_layout.addWidget(input_frame)

        # Status
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 11px; padding: 4px 2px;")
        chat_layout.addWidget(self.status_label)

        layout.addWidget(chat_area, stretch=1)

        # ── Right: Sidebar ──
        right_sidebar = QWidget()
        right_sidebar.setFixedWidth(260)
        right_sidebar.setStyleSheet("""
            QWidget {
                background-color: rgba(12,12,20,0.5);
                border-left: 1px solid rgba(255,255,255,0.04);
            }
        """)
        right_layout = QVBoxLayout(right_sidebar)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        # Workspace panel
        self.workspace_panel = WorkspacePanel(self.config, self.workspace_mgr, self)
        self.workspace_panel.folders_changed.connect(self._save_current_session)
        right_layout.addWidget(self.workspace_panel)

        # File ops log
        log_frame = QFrame()
        log_frame.setObjectName("Card")
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(12, 10, 12, 10)
        log_layout.setSpacing(6)

        log_header = QLabel("📋 File Operations Log")
        log_header.setStyleSheet("font-size: 12px; font-weight: bold; color: #a6e3a1;")
        log_layout.addWidget(log_header)

        self.file_ops_log = QListWidget()
        self.file_ops_log.setStyleSheet("""
            QListWidget {
                font-size: 10px;
                background-color: rgba(15,15,23,0.6);
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 3px 6px;
            }
        """)
        log_layout.addWidget(self.file_ops_log)

        right_layout.addWidget(log_frame)

        right_layout.addStretch()

        layout.addWidget(right_sidebar)

        # Welcome message
        self._add_system_message("Welcome to AirLLMEasy! Select a model and start chatting.")
        if self.config.workspace_folders:
            self._add_system_message(
                f"📁 Workspace loaded with {len(self.config.workspace_folders)} folder(s). "
                "AI can create, edit, and move files."
            )

    # ─────────────────────────── Backend switching ────────────────────────

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
            self.status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
        else:
            self.status_label.setText("ℹ️ AirLLM: No model loaded — click Load Model")
            self.status_label.setStyleSheet("color: #fab387; font-size: 11px;")

    def _refresh_models(self):
        """Refresh the list of available models."""
        self.model_combo.clear()

        if self.ollama_radio.isChecked():
            if self.ollama.is_running():
                models = self.ollama.list_models()
                for model in models:
                    self.model_combo.addItem(model.get("name", ""))
                self.status_label.setText("🟢 Connected to Ollama")
                self.status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
            else:
                self.status_label.setText("🔴 Ollama is not running")
                self.status_label.setStyleSheet("color: #f38ba8; font-size: 11px;")

        elif self.lmstudio_radio.isChecked():
            if self.lmstudio.is_running():
                models = self.lmstudio.list_models()
                for model in models:
                    self.model_combo.addItem(model.get("name", ""))
                self.status_label.setText("🟢 Connected to LMStudio")
                self.status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
            else:
                self.status_label.setText("🔴 LMStudio server is not running")
                self.status_label.setStyleSheet("color: #f38ba8; font-size: 11px;")

        if self.model_combo.count() == 0 and not self.airllm_radio.isChecked():
            self.model_combo.addItem("No models available")

    # ─────────────────────────── AirLLM loading ──────────────────────────

    def _load_airllm_model(self):
        """Load a model in AirLLM."""
        dialog = ModelSelectorDialog(self.airllm, self)
        if dialog.exec() == QDialog.Accepted:
            model_path, model_type = dialog.get_selection()
            if not model_path:
                QMessageBox.warning(self, "Warning", "No model selected!")
                return
            self._start_model_load(model_path, model_type)

    def _start_model_load(self, model_path: str, model_type: str):
        self.load_model_btn.setEnabled(False)
        self.status_label.setText(f"⏳ Loading {model_path}...")

        self._pending_model_path = model_path
        self._pending_model_type = model_type

        self.load_worker = LoadModelWorker(
            self.airllm, model_path,
            self.config.airllm_compression, model_type
        )
        self.load_worker.progress.connect(lambda s: self.status_label.setText(s))
        self.load_worker.missing_package.connect(self._on_missing_package)
        self.load_worker.finished.connect(self._on_model_loaded)
        self.load_worker.start()

    def _on_missing_package(self, marker: str):
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
            self._add_system_message("✅ Package installed! Trying to load the model again…")
            self._start_model_load(self._pending_model_path, self._pending_model_type)

    def _on_model_loaded(self, success: bool, message: str):
        self.load_model_btn.setEnabled(True)
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: #a6e3a1; font-size: 11px;")
            self._add_system_message(f"Model loaded: {self.airllm.get_loaded_model_name()}")
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: #f38ba8; font-size: 11px;")

    # ─────────────────────────── Send Message ─────────────────────────────

    def _send_message(self):
        """Send a message to the model."""
        message = self.input_text.toPlainText().strip()
        if not message:
            return

        if self.chat_worker and self.chat_worker.isRunning():
            QMessageBox.warning(self, "Warning", "Wait for the previous response!")
            return

        # Build system prompt with file ops context & extensions
        system_prompt = self.config.system_prompt
        
        # Inject standard file tools
        if self.config.file_ops_enabled and self.workspace_mgr.allowed_folders:
            system_prompt += self.workspace_mgr.build_system_prompt_fragment()
            
        # Inject extension tools
        ext_tools = self.extension_mgr.get_all_tools()
        if ext_tools:
            tools_desc = "\n".join([f"• {t['name']} — {t['description']} | Format: {t.get('format', '{}')}" for t in ext_tools])
            system_prompt += f"\n\nAVAILABLE EXTENSION TOOLS:\nYou may also use the following extension tools by outputting a JSON <tool_call> block containing the fields described above.\n{tools_desc}\n"

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
            system_prompt=system_prompt,
            max_tokens=self.tokens_spin.value(),
            temperature=self.temp_spin.value(),
            conversation_history=self.conversation_history[:-1]  # exclude the message we just added
        )
        self.chat_worker.token_received.connect(self._on_token_received)
        self.chat_worker.finished.connect(self._on_chat_finished)
        self.chat_worker.error.connect(self._on_chat_error)

        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ Thinking…")
        self.chat_worker.start()

    # ─────────────────────────── Chat Display ─────────────────────────────

    def _add_system_message(self, message: str):
        self.chat_display.append(
            f'<p style="color: #6c7086; font-style: italic; font-size: 12px; '
            f'padding: 6px 10px; background-color: rgba(255,255,255,0.02); '
            f'border-radius: 8px; margin: 4px 0;">📋 {message}</p>'
        )

    def _add_user_message(self, message: str, save: bool = True):
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.chat_display.append(
            f'<div style="margin: 8px 0;">'
            f'<p style="color: #89b4fa; font-weight: bold; font-size: 13px;">👤 You</p>'
            f'<p style="margin-left: 24px; color: #e0e0ec; line-height: 1.5;">{escaped}</p>'
            f'</div>'
        )
        if save:
            self.conversation_history.append({"role": "user", "content": message})
            self._save_current_session()

    def _add_assistant_header(self):
        self.chat_display.append(
            f'<div style="margin: 8px 0;">'
            f'<p style="color: #a6e3a1; font-weight: bold; font-size: 13px;">🤖 Assistant</p>'
            f'<p style="margin-left: 24px; color: #e0e0ec; line-height: 1.5;">'
        )

    def _on_token_received(self, token: str):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(token)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def _on_chat_finished(self, response: str):
        self.chat_display.append("</p></div><br>")
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send 🚀")
        self.conversation_history.append({"role": "assistant", "content": response})
        self._save_current_session()

        # Process file operations from the response
        if self.config.file_ops_enabled and self.workspace_mgr.allowed_folders:
            tool_results = self._process_file_operations(response)
            
            # Auto-continue: if we only did read/list operations, feed results back
            if tool_results and self._should_auto_continue(tool_results):
                self._auto_continue(tool_results)

    def _should_auto_continue(self, tool_results):
        """Check if tool results are read-only and need a follow-up from the AI."""
        if not tool_results:
            return False
        read_tools = {"read_file", "list_directory"}
        return all(r["tool"] in read_tools for r in tool_results)

    def _auto_continue(self, tool_results):
        """Feed tool results back to the AI so it can continue with write operations."""
        # Build a summary of what was read for the AI (FULL context)
        ai_followup = "Tool execution results:\n"
        for r in tool_results:
            ai_followup += f"\n[{r['tool']}] {r['result']}\n"
        ai_followup += "\nAbove is the content you requested. Now, please fulfill the original user request by using the appropriate tool calls (e.g., modify_file or create_file)."
        
        # Add to history as a system observation
        self.conversation_history.append({"role": "system", "content": ai_followup})
        self._add_system_message("🔄 Data retrieved. AI is now calculating the edit...")
        
        # Re-run the chain
        self._add_assistant_header()
        
        system_prompt = self.config.system_prompt
        if self.config.file_ops_enabled and self.workspace_mgr.allowed_folders:
            system_prompt += self.workspace_mgr.build_system_prompt_fragment()

        if self.ollama_radio.isChecked():
            backend = self.ollama
            model = self.model_combo.currentText()
        elif self.lmstudio_radio.isChecked():
            backend = self.lmstudio
            model = self.model_combo.currentText()
        else:
            backend = self.airllm
            model = None

        self.chat_worker = ChatWorker(
            backend, model, ai_followup,
            system_prompt=system_prompt,
            max_tokens=self.tokens_spin.value(),
            temperature=self.temp_spin.value(),
            conversation_history=self.conversation_history[:-1]
        )
        self.chat_worker.token_received.connect(self._on_token_received)
        self.chat_worker.finished.connect(self._on_chat_finished)
        self.chat_worker.error.connect(self._on_chat_error)
        self.chat_worker.start()

    def _on_chat_error(self, error: str):
        self.chat_display.append(
            f'<p style="color: #f38ba8; padding: 6px 10px; '
            f'background-color: rgba(243,139,168,0.08); border-radius: 8px;">'
            f'❌ Error: {error}</p>'
        )
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send 🚀")

    def _save_current_session(self):
        sid = self.config.current_session_id
        if not sid: return
        self.config.chat_sessions.setdefault(sid, {})
        self.config.chat_sessions[sid]["history"] = self.conversation_history
        self.config.chat_sessions[sid]["workspaces"] = self.config.workspace_folders
        self.config.save()

    def _load_sessions(self):
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        sessions = self.config.chat_sessions
        if not sessions:
            import uuid
            sid = str(uuid.uuid4())
            sessions[sid] = {"name": "Session 1", "history": [], "workspaces": []}
            self.config.current_session_id = sid
            self.config.save()
            
        for sid, sdata in sessions.items():
            self.session_combo.addItem(sdata.get("name", "Unnamed Session"), userData=sid)
            
        idx = self.session_combo.findData(self.config.current_session_id)
        if idx >= 0:
            self.session_combo.setCurrentIndex(idx)
        self.session_combo.blockSignals(False)
        self._on_session_changed(max(0, idx))

    def _on_session_changed(self, idx):
        if idx < 0: return
        sid = self.session_combo.itemData(idx)
        if sid != self.config.current_session_id:
            self._save_current_session()
            self.config.current_session_id = sid
        
        session_data = self.config.chat_sessions.get(sid, {})
        self.conversation_history = session_data.get("history", [])
        self.config.workspace_folders = session_data.get("workspaces", [])
        self.config.save()
        
        # Logic to refresh workspace panel will rebuild the manager state
        self.workspace_panel._load_folders()
        self._refresh_chat_display()
        
    def _refresh_chat_display(self):
        self.chat_display.clear()
        if not self.conversation_history:
            self._add_system_message("Session started! Chat and Workspaces ready.")
        for msg in self.conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                self._add_user_message(content, save=False)
            elif role == "assistant":
                escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                self.chat_display.append(
                    f'<div style="margin: 8px 0;">'
                    f'<p style="color: #a6e3a1; font-weight: bold; font-size: 13px;">🤖 Assistant</p>'
                    f'<p style="margin-left: 24px; color: #e0e0ec; line-height: 1.5;">{escaped}</p>'
                    f'</div><br>'
                )
            elif role == "system":
                self._add_system_message(content)

    def _create_new_session(self):
        self._save_current_session()
        import uuid
        sid = str(uuid.uuid4())
        name = f"Session {self.session_combo.count() + 1}"
        self.config.chat_sessions[sid] = {"name": name, "history": [], "workspaces": []}
        self.config.current_session_id = sid
        self.config.save()
        self._load_sessions()

    def _delete_session(self):
        sid = self.config.current_session_id
        if len(self.config.chat_sessions) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete the last session.")
            return
            
        reply = QMessageBox.question(self, "Delete Session", "Are you sure you want to delete this session?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            del self.config.chat_sessions[sid]
            self.config.current_session_id = list(self.config.chat_sessions.keys())[0]
            self.config.save()
            self._load_sessions()
            
    def _clear_chat(self):
        self.conversation_history.clear()
        self._save_current_session()
        self._refresh_chat_display()

    # ─────────────────────────── File Operations ──────────────────────────

    def _process_file_operations(self, response: str):
        """Parse and execute file operations / extension tools from the AI response.
        
        Returns a list of dicts with 'tool' and 'result' for auto-continue logic.
        """
        tool_calls = WorkspaceManager.parse_tool_calls(response)
        print(f"DEBUG: Parsed {len(tool_calls)} tool calls from response.")
        if not tool_calls:
            if "<tool_call>" in response:
                print("DEBUG: Found <tool_call> tag but parsing failed! Check JSON format.")
            return []

        # Build lookup table for extension handlers
        ext_handlers = {t["name"]: t["handler"] for t in self.extension_mgr.get_all_tools()}
        
        results = []

        for tc in tool_calls:
            tool_name = tc.get("tool", "unknown").lower()
            
            # Check if it's an extension tool first
            if tool_name in ext_handlers:
                try:
                    result = ext_handlers[tool_name](tc)
                except Exception as e:
                    result = f"Error executing plugin tool {tool_name}: {e}"
            else:
                # Fallback to standard file operations
                result = self.workspace_mgr.execute_tool_call(tc)

            results.append({"tool": tool_name, "result": str(result)})

            # Log to the file ops panel
            is_error = str(result).startswith("Error")
            icon = "❌" if is_error else "✅"
            color = QColor("#f38ba8") if is_error else QColor("#a6e3a1")

            item = QListWidgetItem(f"{icon} {tool_name}: {str(result)[:60]}")
            item.setForeground(color)
            item.setToolTip(str(result))
            self.file_ops_log.addItem(item)
            self.file_ops_log.scrollToBottom()

            # Show in chat (short summary for the user)
            if is_error:
                self._add_system_message(f"❌ Tool failed: {result[:100]}...")
            else:
                # If it's a read operation, just show a confirmation instead of the whole file
                if tool_name in ["read_file", "list_directory"]:
                    path = tc.get("path", "the file")
                    self._add_system_message(f"✅ Successfully read {path}")
                else:
                    self._add_system_message(f"✅ Executed {tool_name}: {str(result)[:100]}...")
        
        return results
