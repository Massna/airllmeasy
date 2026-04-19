"""Aba de download de modelos."""
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
    """Worker thread para downloads."""
    progress = Signal(str, float)  # status, percentage (-1 para indeterminado)
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
                self.finished.emit(True, "Download concluído!")
            else:
                self.finished.emit(False, "Falha no download")
        except Exception as e:
            self.finished.emit(False, str(e))


class DownloadTab(QWidget):
    """Aba para download e gerenciamento de modelos."""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.ollama = OllamaBackend(config.ollama_url)
        self.lmstudio = LMStudioBackend(config.lmstudio_url)
        self.download_worker = None
        
        self._setup_ui()
        self.refresh_for_backend()
    
    def _setup_ui(self):
        """Configura a interface da aba."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Splitter para dividir modelos instalados e disponíveis
        splitter = QSplitter(Qt.Horizontal)
        
        # === Painel esquerdo: Modelos Instalados ===
        installed_panel = QGroupBox("📦 Modelos Instalados")
        installed_layout = QVBoxLayout(installed_panel)
        
        # Lista de modelos instalados
        self.installed_list = QListWidget()
        self.installed_list.setMinimumWidth(300)
        installed_layout.addWidget(self.installed_list)
        
        # Botões de ação para modelos instalados
        installed_buttons = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Atualizar")
        self.refresh_btn.clicked.connect(self.refresh_models)
        installed_buttons.addWidget(self.refresh_btn)
        
        self.delete_btn = QPushButton("🗑️ Remover")
        self.delete_btn.clicked.connect(self._delete_selected_model)
        installed_buttons.addWidget(self.delete_btn)
        
        installed_layout.addLayout(installed_buttons)
        
        splitter.addWidget(installed_panel)
        
        # === Painel direito: Download ===
        download_panel = QGroupBox("📥 Baixar Novo Modelo")
        download_layout = QVBoxLayout(download_panel)
        
        # Seletor de modelo (Ollama) ou busca (LMStudio)
        self.model_selector_label = QLabel("Selecione um modelo:")
        download_layout.addWidget(self.model_selector_label)
        
        # Combo para Ollama
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(300)
        download_layout.addWidget(self.model_combo)
        
        # Frame para LMStudio (HuggingFace)
        self.hf_frame = QFrame()
        hf_layout = QVBoxLayout(self.hf_frame)
        hf_layout.setContentsMargins(0, 0, 0, 0)
        
        hf_layout.addWidget(QLabel("Repositório HuggingFace:"))
        self.hf_repo_input = QLineEdit()
        self.hf_repo_input.setPlaceholderText("ex: TheBloke/Llama-2-7B-GGUF")
        hf_layout.addWidget(self.hf_repo_input)
        
        hf_layout.addWidget(QLabel("Nome do arquivo GGUF:"))
        self.hf_file_input = QLineEdit()
        self.hf_file_input.setPlaceholderText("ex: llama-2-7b.Q4_K_M.gguf")
        hf_layout.addWidget(self.hf_file_input)
        
        # Modelos populares para LMStudio
        hf_layout.addWidget(QLabel("Ou escolha um modelo popular:"))
        self.hf_popular_combo = QComboBox()
        self.hf_popular_combo.currentIndexChanged.connect(self._on_popular_model_selected)
        hf_layout.addWidget(self.hf_popular_combo)
        
        download_layout.addWidget(self.hf_frame)
        
        # Botão de download
        self.download_btn = QPushButton("⬇️ Baixar Modelo")
        self.download_btn.setMinimumHeight(40)
        font = self.download_btn.font()
        font.setPointSize(12)
        self.download_btn.setFont(font)
        self.download_btn.clicked.connect(self._start_download)
        download_layout.addWidget(self.download_btn)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        download_layout.addWidget(self.progress_bar)
        
        # Status do download
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        download_layout.addWidget(self.status_label)
        
        download_layout.addStretch()
        
        splitter.addWidget(download_panel)
        
        # Proporção do splitter
        splitter.setSizes([400, 500])
        
        layout.addWidget(splitter)
        
        # Status do backend
        self.backend_status = QLabel()
        layout.addWidget(self.backend_status)
    
    def refresh_for_backend(self):
        """Atualiza a interface para o backend atual."""
        is_ollama = self.config.download_backend == "ollama"
        
        # Mostra/esconde elementos conforme backend
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
        """Popula lista de modelos Ollama disponíveis."""
        self.model_combo.clear()
        for model in OllamaBackend.get_available_models():
            self.model_combo.addItem(model)
    
    def _populate_lmstudio_models(self):
        """Popula lista de modelos populares para LMStudio."""
        self.hf_popular_combo.clear()
        self.hf_popular_combo.addItem("-- Selecione --", None)
        for model in LMStudioBackend.get_popular_models():
            display = f"{model['repo'].split('/')[-1]} - {model['file']}"
            self.hf_popular_combo.addItem(display, model)
    
    def _on_popular_model_selected(self, index):
        """Quando um modelo popular é selecionado."""
        data = self.hf_popular_combo.currentData()
        if data:
            self.hf_repo_input.setText(data["repo"])
            self.hf_file_input.setText(data["file"])
    
    def _check_ollama_status(self):
        """Verifica status do Ollama."""
        if self.ollama.is_running():
            self.backend_status.setText("✅ Ollama está rodando")
            self.backend_status.setStyleSheet("color: #a6e3a1;")
        else:
            self.backend_status.setText("❌ Ollama não está rodando. Inicie com 'ollama serve'")
            self.backend_status.setStyleSheet("color: #f38ba8;")
    
    def _check_lmstudio_status(self):
        """Verifica status do LMStudio."""
        if self.lmstudio.is_running():
            self.backend_status.setText("✅ LMStudio servidor está rodando")
            self.backend_status.setStyleSheet("color: #a6e3a1;")
        else:
            self.backend_status.setText("ℹ️ LMStudio: Abra o app e inicie o servidor local")
            self.backend_status.setStyleSheet("color: #fab387;")
    
    def refresh_models(self):
        """Atualiza lista de modelos instalados."""
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
            self.installed_list.addItem("Nenhum modelo instalado")
    
    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para string legível."""
        if size_bytes == 0:
            return "?"
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _start_download(self):
        """Inicia o download de um modelo."""
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, "Aviso", "Já existe um download em andamento!")
            return
        
        is_ollama = self.config.download_backend == "ollama"
        
        if is_ollama:
            model_name = self.model_combo.currentText().strip()
            if not model_name:
                QMessageBox.warning(self, "Aviso", "Selecione ou digite um modelo!")
                return
            
            if not self.ollama.is_running():
                QMessageBox.warning(
                    self, "Erro", 
                    "Ollama não está rodando!\nInicie com: ollama serve"
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
                    self, "Aviso", 
                    "Preencha o repositório e nome do arquivo!"
                )
                return
            
            self.download_worker = DownloadWorker(
                self.lmstudio, filename, is_ollama=False,
                repo=repo, filename=filename
            )
        
        # Conecta sinais
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        
        # Atualiza UI
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Iniciando download...")
        
        self.download_worker.start()
    
    def _on_download_progress(self, status: str, percentage: float):
        """Callback de progresso do download."""
        self.status_label.setText(status)
        
        if percentage >= 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(percentage))
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminado
    
    def _on_download_finished(self, success: bool, message: str):
        """Callback quando download termina."""
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
        """Remove o modelo selecionado."""
        current = self.installed_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Aviso", "Selecione um modelo para remover!")
            return
        
        model_id = current.data(Qt.UserRole)
        if not model_id:
            return
        
        reply = QMessageBox.question(
            self, "Confirmar Remoção",
            f"Remover o modelo:\n{model_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.config.download_backend == "ollama":
                success = self.ollama.delete_model(model_id)
            else:
                success = self.lmstudio.delete_model(model_id)
            
            if success:
                self.status_label.setText("✅ Modelo removido!")
                self.status_label.setStyleSheet("color: #a6e3a1;")
                self.refresh_models()
            else:
                self.status_label.setText("❌ Erro ao remover modelo")
                self.status_label.setStyleSheet("color: #f38ba8;")
