"""Model download tab — premium card-based design."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QComboBox,
    QGroupBox, QMessageBox, QLineEdit, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor

from ..utils.config import Config
from ..backends.ollama_backend import OllamaBackend
from ..backends.lmstudio_backend import LMStudioBackend


class DownloadWorker(QThread):
    """Worker thread for downloads."""
    progress = Signal(str, float)  # status, percentage (-1 for indeterminate)
    finished = Signal(bool, str)  # success, message

    def __init__(self, backend, model_name, is_ollama=True, repo=None, filename=None):
        super().__init__()
        self.backend = backend
        self.model_name = model_name
        self.is_ollama = is_ollama
        self.repo = repo
        self.filename = filename

    def run(self):
        try:
            if self.is_ollama:
                success = self.backend.pull_model(
                    self.model_name,
                    progress_callback=lambda s, p: self.progress.emit(s, p)
                )
            else:
                success = self.backend.download_model_hf(
                    self.repo,
                    self.filename,
                    progress_callback=lambda s, p: self.progress.emit(s, p)
                )

            if success:
                self.finished.emit(True, "Download complete!")
            else:
                self.finished.emit(False, "Download failed")
        except Exception as e:
            self.finished.emit(False, str(e))


class DownloadTab(QWidget):
    """Tab for downloading and managing models — premium design."""

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.ollama = OllamaBackend(config.ollama_url)
        self.lmstudio = LMStudioBackend(config.lmstudio_url)
        self.download_worker = None

        self._setup_ui()
        self.refresh_for_backend()

    def _setup_ui(self):
        """Set up the tab interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # Splitter to divide installed and available models
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # === Left Panel: Installed Models ===
        installed_panel = QFrame()
        installed_panel.setObjectName("Card")
        installed_layout = QVBoxLayout(installed_panel)
        installed_layout.setContentsMargins(16, 16, 16, 16)
        installed_layout.setSpacing(12)

        # Header
        header_row = QHBoxLayout()
        installed_icon = QLabel("📦")
        installed_icon.setStyleSheet("font-size: 18px;")
        header_row.addWidget(installed_icon)

        installed_title = QLabel(t("download.title", "Installed Models"))
        installed_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #b4befe;")
        header_row.addWidget(installed_title)
        header_row.addStretch()

        model_count_label = QLabel()
        model_count_label.setObjectName("Subtitle")
        self._model_count_label = model_count_label
        header_row.addWidget(model_count_label)

        installed_layout.addLayout(header_row)

        # Installed models list
        self.installed_list = QListWidget()
        self.installed_list.setMinimumWidth(300)
        installed_layout.addWidget(self.installed_list)

        # Action buttons
        installed_buttons = QHBoxLayout()
        installed_buttons.setSpacing(8)

        self.refresh_btn = QPushButton(f"🔄 {t('download.refresh', 'Refresh')}")
        self.refresh_btn.setObjectName("GhostBtn")
        self.refresh_btn.setFixedHeight(34)
        self.refresh_btn.clicked.connect(self.refresh_models)
        installed_buttons.addWidget(self.refresh_btn)

        self.delete_btn = QPushButton(f"🗑 {t('download.remove', 'Remove')}")
        self.delete_btn.setObjectName("DangerBtn")
        self.delete_btn.setFixedHeight(34)
        self.delete_btn.clicked.connect(self._delete_selected_model)
        installed_buttons.addWidget(self.delete_btn)

        installed_layout.addLayout(installed_buttons)

        splitter.addWidget(installed_panel)

        # === Right Panel: Download ===
        download_panel = QFrame()
        download_panel.setObjectName("Card")
        download_layout = QVBoxLayout(download_panel)
        download_panel.setContentsMargins(16, 16, 16, 16)
        download_layout.setSpacing(12)

        # Header
        dl_header_row = QHBoxLayout()
        dl_icon = QLabel("📥")
        dl_icon.setStyleSheet("font-size: 18px;")
        dl_header_row.addWidget(dl_icon)

        dl_title = QLabel(t("download.new_model", "Download New Model"))
        dl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #89b4fa;")
        dl_header_row.addWidget(dl_title)
        dl_header_row.addStretch()
        download_layout.addLayout(dl_header_row)

        # Model selector (Ollama)
        self.model_selector_label = QLabel(t("download.select_model", "Select a model:"))
        self.model_selector_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        download_layout.addWidget(self.model_selector_label)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(300)
        download_layout.addWidget(self.model_combo)

        # Frame for LMStudio (HuggingFace)
        self.hf_frame = QFrame()
        hf_layout = QVBoxLayout(self.hf_frame)
        hf_layout.setContentsMargins(0, 0, 0, 0)
        hf_layout.setSpacing(8)

        hf_repo_label = QLabel(t("download.hf_repo", "HuggingFace Repository:"))
        hf_repo_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        hf_layout.addWidget(hf_repo_label)

        self.hf_repo_input = QLineEdit()
        self.hf_repo_input.setPlaceholderText("e.g.: TheBloke/Llama-2-7B-GGUF")
        hf_layout.addWidget(self.hf_repo_input)

        hf_file_label = QLabel(t("download.hf_file", "GGUF file name:"))
        hf_file_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        hf_layout.addWidget(hf_file_label)

        self.hf_file_input = QLineEdit()
        self.hf_file_input.setPlaceholderText("e.g.: llama-2-7b.Q4_K_M.gguf")
        hf_layout.addWidget(self.hf_file_input)

        # Popular models
        popular_label = QLabel(t("download.popular", "Or choose a popular model:"))
        popular_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        hf_layout.addWidget(popular_label)

        self.hf_popular_combo = QComboBox()
        self.hf_popular_combo.currentIndexChanged.connect(self._on_popular_model_selected)
        hf_layout.addWidget(self.hf_popular_combo)

        download_layout.addWidget(self.hf_frame)

        self.download_btn = QPushButton(f"⬇️ {t('download.btn', 'Download Model')}")
        self.download_btn.setObjectName("SuccessBtn")
        self.download_btn.setMinimumHeight(42)
        self.download_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #a6e3a1, stop:1 #94e2d5);
                color: #0f0f17;
                border-radius: 12px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background: #94e2d5;
            }
            QPushButton:disabled {
                background-color: #1e1e2e;
                color: #45475a;
            }
        """)
        self.download_btn.clicked.connect(self._start_download)
        download_layout.addWidget(self.download_btn)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(26)
        download_layout.addWidget(self.progress_bar)

        # Status
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 12px;")
        download_layout.addWidget(self.status_label)

        download_layout.addStretch()

        splitter.addWidget(download_panel)

        splitter.setSizes([420, 520])

        layout.addWidget(splitter)

        # Backend status bar
        status_frame = QFrame()
        status_frame.setObjectName("Card")
        status_frame.setFixedHeight(40)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(14, 0, 14, 0)

        self.backend_status = QLabel()
        self.backend_status.setStyleSheet("font-size: 12px;")
        status_layout.addWidget(self.backend_status)
        status_layout.addStretch()

        layout.addWidget(status_frame)

    def refresh_for_backend(self):
        """Update the interface for the current backend."""
        is_ollama = self.config.download_backend == "ollama"

        self.model_combo.setVisible(is_ollama)
        self.model_selector_label.setVisible(is_ollama)
        self.hf_frame.setVisible(not is_ollama)

        if is_ollama:
            self._populate_ollama_models()
            self._check_ollama_status()
        else:
            self._populate_lmstudio_models()
            self._check_lmstudio_status()

        self.refresh_models()

    def _populate_ollama_models(self):
        self.model_combo.clear()
        for model in OllamaBackend.get_available_models():
            self.model_combo.addItem(model)

    def _populate_lmstudio_models(self):
        self.hf_popular_combo.clear()
        self.hf_popular_combo.addItem(f"-- {t('download.select', 'Select')} --", None)
        for model in LMStudioBackend.get_popular_models():
            display = f"{model['repo'].split('/')[-1]} — {model['file']}"
            self.hf_popular_combo.addItem(display, model)

    def _on_popular_model_selected(self, index):
        data = self.hf_popular_combo.currentData()
        if data:
            self.hf_repo_input.setText(data["repo"])
            self.hf_file_input.setText(data["file"])

    def _check_ollama_status(self):
        if self.ollama.is_running():
            self.backend_status.setText(f"🟢 {t('download.ollama_running', 'Ollama is running')}")
            self.backend_status.setStyleSheet("color: #a6e3a1; font-size: 12px;")
        else:
            self.backend_status.setText(f"🔴 {t('download.ollama_not_running', 'Ollama is not running — start with')}")
            self.backend_status.setStyleSheet("color: #f38ba8; font-size: 12px;")

    def _check_lmstudio_status(self):
        if self.lmstudio.is_running():
            self.backend_status.setText(f"🟢 {t('download.lmstudio_running', 'LMStudio server is running')}")
            self.backend_status.setStyleSheet("color: #a6e3a1; font-size: 12px;")
        else:
            self.backend_status.setText(f"🟡 {t('download.lmstudio_not_running', 'LMStudio: Open the app and start the local server')}")
            self.backend_status.setStyleSheet("color: #fab387; font-size: 12px;")

    def refresh_models(self):
        """Refresh the installed models list."""
        self.installed_list.clear()

        if self.config.download_backend == "ollama":
            models = self.ollama.list_models()
            for model in models:
                name = model.get("name", "")
                size = model.get("size", 0)
                size_str = self._format_size(size)
                item = QListWidgetItem(f"🤖  {name}  •  {size_str}")
                item.setData(Qt.UserRole, name)
                self.installed_list.addItem(item)
        else:
            models = self.lmstudio.list_local_models()
            for model in models:
                name = model.get("name", "")
                size = model.get("size", 0)
                size_str = self._format_size(size)
                item = QListWidgetItem(f"🤖  {name}  •  {size_str}")
                item.setData(Qt.UserRole, model.get("path", name))
                self.installed_list.addItem(item)

        count = self.installed_list.count()
        if count == 0:
            empty_item = QListWidgetItem(f"   {t('download.no_models', 'No models installed')}")
            empty_item.setForeground(QColor("#6c7086"))
            empty_item.setFlags(Qt.NoItemFlags)
            self.installed_list.addItem(empty_item)
            self._model_count_label.setText(f"0 {t('download.models', 'models')}")
        else:
            self._model_count_label.setText(f"{count} {t('download.models', 'models')}")

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes == 0:
            return "?"
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def _start_download(self):
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, t("dialogs.warning", "Warning"), t("download.already_in_progress", "A download is already in progress!"))
            return

        is_ollama = self.config.download_backend == "ollama"

        if is_ollama:
            model_name = self.model_combo.currentText().strip()
            if not model_name:
                QMessageBox.warning(self, t("dialogs.warning", "Warning"), t("download.select_type_model", "Select or type a model!"))
                return

            if not self.ollama.is_running():
                QMessageBox.warning(
                    self, t("dialogs.error", "Error"),
                    t("download.ollama_error", "Ollama is not running!\nStart with: ollama serve")
                )
                return

            self.download_worker = DownloadWorker(
                self.ollama, model_name, is_ollama=True
            )
        else:
            repo = self.hf_repo_input.text().strip()
            filename = self.hf_file_input.text().strip()

            if not repo or not filename:
                QMessageBox.warning(
                    self, t("dialogs.warning", "Warning"),
                    t("download.fill_repo", "Fill in the repository and file name!")
                )
                return

            self.download_worker = DownloadWorker(
                self.lmstudio, filename, is_ollama=False,
                repo=repo, filename=filename
            )

        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)

        self.download_btn.setEnabled(False)
        self.download_btn.setText(f"⏳ {t('download.downloading', 'Downloading…')}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(t("download.starting", "Starting download..."))

        self.download_worker.start()

    def _on_download_progress(self, status: str, percentage: float):
        self.status_label.setText(status)

        if percentage >= 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(percentage))
        else:
            self.progress_bar.setRange(0, 0)

    def _on_download_finished(self, success: bool, message: str):
        self.download_btn.setEnabled(True)
        self.download_btn.setText(f"⬇️ {t('download.btn', 'Download Model')}")
        self.progress_bar.setVisible(False)

        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
            self.refresh_models()
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: #f38ba8; font-size: 12px;")

    def _delete_selected_model(self):
        current = self.installed_list.currentItem()
        if not current:
            QMessageBox.warning(self, t("dialogs.warning", "Warning"), t("download.select_remove", "Select a model to remove!"))
            return

        model_id = current.data(Qt.UserRole)
        if not model_id:
            return

        reply = QMessageBox.question(
            self, t("download.confirm_removal", "Confirm Removal"),
            f"{t('download.remove_confirm', 'Remove the model:')}\n{model_id}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.config.download_backend == "ollama":
                success = self.ollama.delete_model(model_id)
            else:
                success = self.lmstudio.delete_model(model_id)

            if success:
                self.status_label.setText(f"✅ {t('download.removed', 'Model removed!')}")
                self.status_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
                self.refresh_models()
            else:
                self.status_label.setText(f"❌ {t('download.error_removing', 'Error removing model')}")
                self.status_label.setStyleSheet("color: #f38ba8; font-size: 12px;")
