"""Model download tab."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QProgressBar, QComboBox,
    QGroupBox, QMessageBox, QLineEdit, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

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
    """Tab for downloading and managing models."""
    
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
        layout.setSpacing(15)
        
        # Splitter to divide installed and available models
        splitter = QSplitter(Qt.Horizontal)
        
        # === Left Panel: Installed Models ===
        installed_panel = QGroupBox("📦 Installed Models")
        installed_layout = QVBoxLayout(installed_panel)
        
        # Installed models list
        self.installed_list = QListWidget()
        self.installed_list.setMinimumWidth(300)
        installed_layout.addWidget(self.installed_list)
        
        # Action buttons for installed models
        installed_buttons = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh_models)
        installed_buttons.addWidget(self.refresh_btn)
        
        self.delete_btn = QPushButton("🗑️ Remove")
        self.delete_btn.clicked.connect(self._delete_selected_model)
        installed_buttons.addWidget(self.delete_btn)
        
        installed_layout.addLayout(installed_buttons)
        
        splitter.addWidget(installed_panel)
        
        # === Right Panel: Download ===
        download_panel = QGroupBox("📥 Download New Model")
        download_layout = QVBoxLayout(download_panel)
        
        # Model selector (Ollama) or search (LMStudio)
        self.model_selector_label = QLabel("Select a model:")
        download_layout.addWidget(self.model_selector_label)
        
        # Combo for Ollama
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(300)
        download_layout.addWidget(self.model_combo)
        
        # Frame for LMStudio (HuggingFace)
        self.hf_frame = QFrame()
        hf_layout = QVBoxLayout(self.hf_frame)
        hf_layout.setContentsMargins(0, 0, 0, 0)
        
        hf_layout.addWidget(QLabel("HuggingFace Repository:"))
        self.hf_repo_input = QLineEdit()
        self.hf_repo_input.setPlaceholderText("e.g.: TheBloke/Llama-2-7B-GGUF")
        hf_layout.addWidget(self.hf_repo_input)
        
        hf_layout.addWidget(QLabel("GGUF file name:"))
        self.hf_file_input = QLineEdit()
        self.hf_file_input.setPlaceholderText("e.g.: llama-2-7b.Q4_K_M.gguf")
        hf_layout.addWidget(self.hf_file_input)
        
        # Popular models for LMStudio
        hf_layout.addWidget(QLabel("Or choose a popular model:"))
        self.hf_popular_combo = QComboBox()
        self.hf_popular_combo.currentIndexChanged.connect(self._on_popular_model_selected)
        hf_layout.addWidget(self.hf_popular_combo)
        
        download_layout.addWidget(self.hf_frame)
        
        # Download button
        self.download_btn = QPushButton("⬇️ Download Model")
        self.download_btn.setMinimumHeight(40)
        font = self.download_btn.font()
        font.setPointSize(12)
        self.download_btn.setFont(font)
        self.download_btn.clicked.connect(self._start_download)
        download_layout.addWidget(self.download_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        download_layout.addWidget(self.progress_bar)
        
        # Download status
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        download_layout.addWidget(self.status_label)
        
        download_layout.addStretch()
        
        splitter.addWidget(download_panel)
        
        # Splitter proportion
        splitter.setSizes([400, 500])
        
        layout.addWidget(splitter)
        
        # Backend status
        self.backend_status = QLabel()
        layout.addWidget(self.backend_status)
    
    def refresh_for_backend(self):
        """Update the interface for the current backend."""
        is_ollama = self.config.download_backend == "ollama"
        
        # Show/hide elements based on backend
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
        """Populate the list of available Ollama models."""
        self.model_combo.clear()
        for model in OllamaBackend.get_available_models():
            self.model_combo.addItem(model)
    
    def _populate_lmstudio_models(self):
        """Populate the list of popular models for LMStudio."""
        self.hf_popular_combo.clear()
        self.hf_popular_combo.addItem("-- Select --", None)
        for model in LMStudioBackend.get_popular_models():
            display = f"{model['repo'].split('/')[-1]} - {model['file']}"
            self.hf_popular_combo.addItem(display, model)
    
    def _on_popular_model_selected(self, index):
        """When a popular model is selected."""
        data = self.hf_popular_combo.currentData()
        if data:
            self.hf_repo_input.setText(data["repo"])
            self.hf_file_input.setText(data["file"])
    
    def _check_ollama_status(self):
        """Check Ollama status."""
        if self.ollama.is_running():
            self.backend_status.setText("✅ Ollama is running")
            self.backend_status.setStyleSheet("color: #a6e3a1;")
        else:
            self.backend_status.setText("❌ Ollama is not running. Start with 'ollama serve'")
            self.backend_status.setStyleSheet("color: #f38ba8;")
    
    def _check_lmstudio_status(self):
        """Check LMStudio status."""
        if self.lmstudio.is_running():
            self.backend_status.setText("✅ LMStudio server is running")
            self.backend_status.setStyleSheet("color: #a6e3a1;")
        else:
            self.backend_status.setText("ℹ️ LMStudio: Open the app and start the local server")
            self.backend_status.setStyleSheet("color: #fab387;")
    
    def refresh_models(self):
        """Refresh the installed models list."""
        self.installed_list.clear()
        
        if self.config.download_backend == "ollama":
            models = self.ollama.list_models()
            for model in models:
                name = model.get("name", "")
                size = model.get("size", 0)
                size_str = self._format_size(size)
                item = QListWidgetItem(f"🤖 {name} ({size_str})")
                item.setData(Qt.UserRole, name)
                self.installed_list.addItem(item)
        else:
            models = self.lmstudio.list_local_models()
            for model in models:
                name = model.get("name", "")
                size = model.get("size", 0)
                size_str = self._format_size(size)
                item = QListWidgetItem(f"🤖 {name} ({size_str})")
                item.setData(Qt.UserRole, model.get("path", name))
                self.installed_list.addItem(item)
        
        if self.installed_list.count() == 0:
            self.installed_list.addItem("No models installed")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to a readable string."""
        if size_bytes == 0:
            return "?"
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _start_download(self):
        """Start downloading a model."""
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, "Warning", "A download is already in progress!")
            return
        
        is_ollama = self.config.download_backend == "ollama"
        
        if is_ollama:
            model_name = self.model_combo.currentText().strip()
            if not model_name:
                QMessageBox.warning(self, "Warning", "Select or type a model!")
                return
            
            if not self.ollama.is_running():
                QMessageBox.warning(
                    self, "Error", 
                    "Ollama is not running!\nStart with: ollama serve"
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
                    self, "Warning", 
                    "Fill in the repository and file name!"
                )
                return
            
            self.download_worker = DownloadWorker(
                self.lmstudio, filename, is_ollama=False,
                repo=repo, filename=filename
            )
        
        # Connect signals
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        
        # Update UI
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting download...")
        
        self.download_worker.start()
    
    def _on_download_progress(self, status: str, percentage: float):
        """Download progress callback."""
        self.status_label.setText(status)
        
        if percentage >= 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(percentage))
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate
    
    def _on_download_finished(self, success: bool, message: str):
        """Callback when download finishes."""
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: #a6e3a1;")
            self.refresh_models()
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: #f38ba8;")
    
    def _delete_selected_model(self):
        """Remove the selected model."""
        current = self.installed_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Warning", "Select a model to remove!")
            return
        
        model_id = current.data(Qt.UserRole)
        if not model_id:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Removal",
            f"Remove the model:\n{model_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.config.download_backend == "ollama":
                success = self.ollama.delete_model(model_id)
            else:
                success = self.lmstudio.delete_model(model_id)
            
            if success:
                self.status_label.setText("✅ Model removed!")
                self.status_label.setStyleSheet("color: #a6e3a1;")
                self.refresh_models()
            else:
                self.status_label.setText("❌ Error removing model")
                self.status_label.setStyleSheet("color: #f38ba8;")
