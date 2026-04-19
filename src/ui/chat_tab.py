"""Aba de chat com modelos de IA."""
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


class ChatWorker(QThread):
    """Worker thread para chat."""
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
                response = "Backend não suportado"
            
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))


class LoadModelWorker(QThread):
    """Worker thread para carregar modelo no AirLLM."""
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, airllm: AirLLMBackend, model_path: str, compression: str, model_type: str = "huggingface"):
        super().__init__()
        self.airllm = airllm
        self.model_path = model_path
        self.compression = compression
        self.model_type = model_type
    
    def run(self):
        success = self.airllm.load_model(
            self.model_path,
            progress_callback=lambda s: self.progress.emit(s),
            compression=self.compression,
            model_type=self.model_type
        )
        if success:
            self.finished.emit(True, "Modelo carregado!")
        else:
            self.finished.emit(False, "Falha ao carregar modelo")


class ModelSelectorDialog(QDialog):
    """Diálogo para selecionar modelo para AirLLM."""
    
    def __init__(self, airllm: AirLLMBackend, parent=None):
        super().__init__(parent)
        self.airllm = airllm
        self.selected_model = None
        self.selected_type = None
        
        self.setWindowTitle("Selecionar Modelo para AirLLM")
        self.setMinimumSize(500, 400)
        self._setup_ui()
        self._load_models()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Instruções
        info_label = QLabel(
            "Selecione um modelo baixado pelo Ollama ou LMStudio para executar com AirLLM:"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Lista de modelos
        self.model_list = QListWidget()
        self.model_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.model_list)

        refresh_row = QHBoxLayout()
        self.airllm_list_refresh_btn = QPushButton("🔄 Atualizar lista")
        self.airllm_list_refresh_btn.setToolTip(
            "Ollama: usa a API (serviço deve estar em execução). LM Studio: varre pastas de modelos."
        )
        self.airllm_list_refresh_btn.clicked.connect(self._load_models)
        refresh_row.addWidget(self.airllm_list_refresh_btn)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)
        
        # Ou digitar manualmente
        layout.addWidget(QLabel("Ou digite um modelo do HuggingFace:"))
        self.hf_input = QComboBox()
        self.hf_input.setEditable(True)
        # Adiciona modelos populares
        for model in AirLLMBackend.get_supported_models():
            self.hf_input.addItem(f"{model['name']} ({model['size']})", model['name'])
        layout.addWidget(self.hf_input)
        
        # Botões
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_models(self):
        """Carrega lista de modelos disponíveis."""
        self.model_list.clear()
        
        # Modelos do Ollama
        ollama_models = self.airllm.list_ollama_models()
        if ollama_models:
            header = QListWidgetItem("📦 Modelos Ollama:")
            header.setFlags(Qt.NoItemFlags)
            self.model_list.addItem(header)
            
            for model in ollama_models:
                item = QListWidgetItem(f"  🦙 {model['name']}")
                item.setData(Qt.UserRole, model)
                self.model_list.addItem(item)
        
        # Modelos do LMStudio (GGUF)
        lmstudio_models = self.airllm.list_lmstudio_models()
        if lmstudio_models:
            header = QListWidgetItem("📦 Modelos LMStudio (GGUF):")
            header.setFlags(Qt.NoItemFlags)
            self.model_list.addItem(header)
            
            for model in lmstudio_models:
                size_mb = model.get('size', 0) / (1024*1024)
                item = QListWidgetItem(f"  📄 {model['name']} ({size_mb:.0f} MB)")
                item.setData(Qt.UserRole, model)
                self.model_list.addItem(item)
        
        if not ollama_models and not lmstudio_models:
            item = QListWidgetItem("Nenhum modelo local encontrado")
            item.setFlags(Qt.NoItemFlags)
            self.model_list.addItem(item)
    
    def get_selection(self):
        """Retorna o modelo selecionado e seu tipo."""
        # Verifica se selecionou da lista
        current = self.model_list.currentItem()
        if current:
            model_data = current.data(Qt.UserRole)
            if model_data:
                return model_data.get('path', model_data.get('name')), model_data.get('type', 'huggingface')
        
        # Verifica se digitou manualmente
        hf_text = self.hf_input.currentText().strip()
        if hf_text:
            # Remove o tamanho se presente
            if " (" in hf_text:
                hf_text = hf_text.split(" (")[0]
            return hf_text, "huggingface"
        
        return None, None


class ChatTab(QWidget):
    """Aba de chat com modelos de IA."""
    
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
        """Configura a interface da aba de chat."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === Configurações do Chat ===
        config_frame = QFrame()
        config_layout = QHBoxLayout(config_frame)
        config_layout.setContentsMargins(0, 0, 0, 0)
        
        # Seletor de backend de execução
        config_layout.addWidget(QLabel("Executar com:"))
        
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
        
        # Seletor de modelo
        config_layout.addWidget(QLabel("Modelo:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        config_layout.addWidget(self.model_combo)
        
        self.refresh_models_btn = QPushButton("🔄")
        self.refresh_models_btn.setMaximumWidth(40)
        self.refresh_models_btn.clicked.connect(self._refresh_models)
        config_layout.addWidget(self.refresh_models_btn)
        
        config_layout.addStretch()
        
        # Botão carregar (para AirLLM)
        self.load_model_btn = QPushButton("📂 Carregar Modelo")
        self.load_model_btn.setVisible(False)
        self.load_model_btn.clicked.connect(self._load_airllm_model)
        config_layout.addWidget(self.load_model_btn)
        
        layout.addWidget(config_frame)
        
        # === Área de Chat ===
        chat_splitter = QSplitter(Qt.Vertical)
        
        # Histórico de conversa
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMinimumHeight(300)
        font = QFont("Consolas", 11)
        self.chat_display.setFont(font)
        chat_splitter.addWidget(self.chat_display)
        
        # Área de input
        input_frame = QFrame()
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.input_text = QPlainTextEdit()
        self.input_text.setMaximumHeight(100)
        self.input_text.setPlaceholderText("Digite sua mensagem aqui...")
        self.input_text.setFont(font)
        input_layout.addWidget(self.input_text)
        
        # Botões de ação
        buttons_layout = QHBoxLayout()
        
        # Parâmetros
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
        
        self.clear_btn = QPushButton("🗑️ Limpar")
        self.clear_btn.clicked.connect(self._clear_chat)
        buttons_layout.addWidget(self.clear_btn)
        
        self.send_btn = QPushButton("📤 Enviar")
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
        
        # Mensagem inicial
        self._add_system_message("Bem-vindo ao AI Local Manager! Selecione um modelo e comece a conversar.")
    
    def _on_exec_backend_changed(self, button):
        """Quando o backend de execução muda."""
        is_airllm = button == self.airllm_radio
        self.load_model_btn.setVisible(is_airllm)
        self.model_combo.setVisible(not is_airllm)
        self.refresh_models_btn.setVisible(not is_airllm)
        
        if not is_airllm:
            self._refresh_models()
        else:
            self._update_airllm_status()
    
    def _update_airllm_status(self):
        """Atualiza status do AirLLM."""
        if self.airllm.is_model_loaded():
            model_name = self.airllm.get_loaded_model_name()
            self.status_label.setText(f"✅ AirLLM: {model_name} carregado")
            self.status_label.setStyleSheet("color: #a6e3a1;")
        else:
            self.status_label.setText("ℹ️ AirLLM: Nenhum modelo carregado")
            self.status_label.setStyleSheet("color: #fab387;")
    
    def _refresh_models(self):
        """Atualiza lista de modelos disponíveis."""
        self.model_combo.clear()
        
        if self.ollama_radio.isChecked():
            if self.ollama.is_running():
                models = self.ollama.list_models()
                for model in models:
                    self.model_combo.addItem(model.get("name", ""))
                self.status_label.setText("✅ Conectado ao Ollama")
                self.status_label.setStyleSheet("color: #a6e3a1;")
            else:
                self.status_label.setText("❌ Ollama não está rodando")
                self.status_label.setStyleSheet("color: #f38ba8;")
        
        elif self.lmstudio_radio.isChecked():
            if self.lmstudio.is_running():
                models = self.lmstudio.list_models()
                for model in models:
                    self.model_combo.addItem(model.get("name", ""))
                self.status_label.setText("✅ Conectado ao LMStudio")
                self.status_label.setStyleSheet("color: #a6e3a1;")
            else:
                self.status_label.setText("❌ LMStudio servidor não está rodando")
                self.status_label.setStyleSheet("color: #f38ba8;")
        
        if self.model_combo.count() == 0 and not self.airllm_radio.isChecked():
            self.model_combo.addItem("Nenhum modelo disponível")
    
    def _load_airllm_model(self):
        """Carrega um modelo no AirLLM."""
        # Mostra diálogo de seleção de modelo
        dialog = ModelSelectorDialog(self.airllm, self)
        
        if dialog.exec() == QDialog.Accepted:
            model_path, model_type = dialog.get_selection()
            
            if not model_path:
                QMessageBox.warning(self, "Aviso", "Nenhum modelo selecionado!")
                return
            
            self.load_model_btn.setEnabled(False)
            self.status_label.setText(f"Carregando {model_path}...")
            
            self.load_worker = LoadModelWorker(
                self.airllm,
                model_path,
                self.config.airllm_compression,
                model_type
            )
            self.load_worker.progress.connect(lambda s: self.status_label.setText(s))
            self.load_worker.finished.connect(self._on_model_loaded)
            self.load_worker.start()
    
    def _on_model_loaded(self, success: bool, message: str):
        """Callback quando modelo AirLLM é carregado."""
        self.load_model_btn.setEnabled(True)
        
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: #a6e3a1;")
            self._add_system_message(f"Modelo carregado: {self.airllm.get_loaded_model_name()}")
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: #f38ba8;")
    
    def _send_message(self):
        """Envia mensagem para o modelo."""
        message = self.input_text.toPlainText().strip()
        if not message:
            return
        
        if self.chat_worker and self.chat_worker.isRunning():
            QMessageBox.warning(self, "Aviso", "Aguarde a resposta anterior!")
            return
        
        # Determina backend
        if self.ollama_radio.isChecked():
            backend = self.ollama
            model = self.model_combo.currentText()
            if not self.ollama.is_running():
                QMessageBox.warning(self, "Erro", "Ollama não está rodando!")
                return
        elif self.lmstudio_radio.isChecked():
            backend = self.lmstudio
            model = self.model_combo.currentText()
            if not self.lmstudio.is_running():
                QMessageBox.warning(self, "Erro", "LMStudio não está rodando!")
                return
        else:  # AirLLM
            backend = self.airllm
            model = None
            if not self.airllm.is_model_loaded():
                QMessageBox.warning(self, "Erro", "Carregue um modelo primeiro!")
                return
        
        # Adiciona mensagem do usuário ao chat
        self._add_user_message(message)
        self.input_text.clear()
        
        # Prepara resposta do assistente
        self._add_assistant_header()
        
        # Inicia worker
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
        """Adiciona mensagem do sistema."""
        self.chat_display.append(
            f'<p style="color: #a6adc8; font-style: italic;">📋 {message}</p>'
        )
    
    def _add_user_message(self, message: str):
        """Adiciona mensagem do usuário."""
        self.chat_display.append(
            f'<p style="color: #89b4fa;"><b>👤 Você:</b></p>'
            f'<p style="margin-left: 20px;">{message}</p>'
        )
        self.conversation_history.append({"role": "user", "content": message})
    
    def _add_assistant_header(self):
        """Adiciona header da resposta do assistente."""
        self.chat_display.append(
            f'<p style="color: #a6e3a1;"><b>🤖 Assistente:</b></p>'
            f'<p style="margin-left: 20px;">'
        )
    
    def _on_token_received(self, token: str):
        """Callback para cada token recebido (streaming)."""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(token)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()
    
    def _on_chat_finished(self, response: str):
        """Callback quando chat termina."""
        self.chat_display.append("</p><br>")
        self.send_btn.setEnabled(True)
        self.conversation_history.append({"role": "assistant", "content": response})
    
    def _on_chat_error(self, error: str):
        """Callback para erro no chat."""
        self.chat_display.append(
            f'<p style="color: #f38ba8;">❌ Erro: {error}</p>'
        )
        self.send_btn.setEnabled(True)
    
    def _clear_chat(self):
        """Limpa o histórico de chat."""
        self.chat_display.clear()
        self.conversation_history.clear()
        self._add_system_message("Conversa limpa. Comece uma nova!")
