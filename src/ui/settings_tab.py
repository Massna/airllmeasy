"""Aba de configurações."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QFrame, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal

from ..utils.config import Config
from ..backends.airllm_backend import AirLLMBackend


class SettingsTab(QWidget):
    """Aba de configurações da aplicação."""
    
    settings_changed = Signal()
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Configura a interface da aba."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # === Backend de Download ===
        download_group = QGroupBox("📥 Backend de Download")
        download_layout = QVBoxLayout(download_group)
        
        self.backend_group = QButtonGroup(self)
        
        # Opção A - Ollama
        ollama_layout = QHBoxLayout()
        self.ollama_radio = QRadioButton("🅰️ Ollama")
        self.ollama_radio.setToolTip("Baixa modelos do registro Ollama")
        self.backend_group.addButton(self.ollama_radio)
        ollama_layout.addWidget(self.ollama_radio)
        
        ollama_layout.addWidget(QLabel("URL:"))
        self.ollama_url_input = QLineEdit()
        self.ollama_url_input.setPlaceholderText("http://localhost:11434")
        ollama_layout.addWidget(self.ollama_url_input)
        
        download_layout.addLayout(ollama_layout)
        
        # Opção B - LMStudio
        lmstudio_layout = QHBoxLayout()
        self.lmstudio_radio = QRadioButton("🅱️ LMStudio")
        self.lmstudio_radio.setToolTip("Baixa modelos GGUF do HuggingFace")
        self.backend_group.addButton(self.lmstudio_radio)
        lmstudio_layout.addWidget(self.lmstudio_radio)
        
        lmstudio_layout.addWidget(QLabel("URL:"))
        self.lmstudio_url_input = QLineEdit()
        self.lmstudio_url_input.setPlaceholderText("http://localhost:1234")
        lmstudio_layout.addWidget(self.lmstudio_url_input)
        
        download_layout.addLayout(lmstudio_layout)
        
        layout.addWidget(download_group)
        
        # === AirLLM ===
        airllm_group = QGroupBox("🚀 AirLLM - Execução Otimizada")
        airllm_layout = QVBoxLayout(airllm_group)
        
        # Compressão
        compression_layout = QHBoxLayout()
        compression_layout.addWidget(QLabel("Compressão:"))
        
        self.compression_combo = QComboBox()
        self.compression_combo.addItem("4-bit (Recomendado)", "4bit")
        self.compression_combo.addItem("8-bit", "8bit")
        self.compression_combo.addItem("Sem compressão", "none")
        compression_layout.addWidget(self.compression_combo)
        
        compression_layout.addStretch()
        airllm_layout.addLayout(compression_layout)
        
        # Status do sistema
        self.system_status_btn = QPushButton("🔍 Verificar Requisitos do Sistema")
        self.system_status_btn.clicked.connect(self._check_system_requirements)
        airllm_layout.addWidget(self.system_status_btn)
        
        self.system_status_label = QLabel()
        self.system_status_label.setWordWrap(True)
        airllm_layout.addWidget(self.system_status_label)
        
        layout.addWidget(airllm_group)
        
        # === Parâmetros de Geração ===
        gen_group = QGroupBox("🎛️ Parâmetros de Geração")
        gen_layout = QVBoxLayout(gen_group)
        
        # Max tokens
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel("Máximo de tokens:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 4096)
        self.max_tokens_spin.setValue(512)
        tokens_layout.addWidget(self.max_tokens_spin)
        tokens_layout.addStretch()
        gen_layout.addLayout(tokens_layout)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperatura:"))
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        temp_layout.addWidget(self.temperature_spin)
        temp_layout.addWidget(QLabel("(0 = determinístico, 2 = criativo)"))
        temp_layout.addStretch()
        gen_layout.addLayout(temp_layout)
        
        layout.addWidget(gen_group)
        
        # === Aparência ===
        appearance_group = QGroupBox("🎨 Aparência")
        appearance_layout = QVBoxLayout(appearance_group)
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Tema:"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("🌙 Escuro", "dark")
        self.theme_combo.addItem("☀️ Claro", "light")
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        appearance_layout.addLayout(theme_layout)
        
        layout.addWidget(appearance_group)
        
        # === Botões de Ação ===
        buttons_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("🔄 Restaurar Padrões")
        self.reset_btn.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(self.reset_btn)
        
        buttons_layout.addStretch()
        
        self.save_btn = QPushButton("💾 Salvar Configurações")
        self.save_btn.setMinimumWidth(150)
        self.save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
        
        layout.addStretch()
    
    def _load_settings(self):
        """Carrega configurações atuais."""
        # Backend
        if self.config.download_backend == "ollama":
            self.ollama_radio.setChecked(True)
        else:
            self.lmstudio_radio.setChecked(True)
        
        # URLs
        self.ollama_url_input.setText(self.config.ollama_url)
        self.lmstudio_url_input.setText(self.config.lmstudio_url)
        
        # Compressão AirLLM
        compression = self.config.airllm_compression
        index = self.compression_combo.findData(compression)
        if index >= 0:
            self.compression_combo.setCurrentIndex(index)
        
        # Parâmetros
        self.max_tokens_spin.setValue(self.config.max_tokens)
        self.temperature_spin.setValue(self.config.temperature)
        
        # Tema
        theme = self.config.theme
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
    
    def _save_settings(self):
        """Salva as configurações."""
        # Backend
        if self.ollama_radio.isChecked():
            self.config.download_backend = "ollama"
        else:
            self.config.download_backend = "lmstudio"
        
        # URLs
        self.config.ollama_url = self.ollama_url_input.text().strip() or "http://localhost:11434"
        self.config.lmstudio_url = self.lmstudio_url_input.text().strip() or "http://localhost:1234"
        
        # Compressão AirLLM
        self.config.airllm_compression = self.compression_combo.currentData()
        
        # Parâmetros
        self.config.max_tokens = self.max_tokens_spin.value()
        self.config.temperature = self.temperature_spin.value()
        
        # Tema
        self.config.theme = self.theme_combo.currentData()
        
        # Salva
        if self.config.save():
            QMessageBox.information(
                self, "Sucesso",
                "Configurações salvas com sucesso!"
            )
            self.settings_changed.emit()
        else:
            QMessageBox.warning(
                self, "Erro",
                "Erro ao salvar configurações!"
            )
    
    def _reset_settings(self):
        """Restaura configurações padrão."""
        reply = QMessageBox.question(
            self, "Confirmar",
            "Restaurar todas as configurações para o padrão?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config.reset()
            self._load_settings()
            QMessageBox.information(
                self, "Sucesso",
                "Configurações restauradas!"
            )
    
    def _check_system_requirements(self):
        """Verifica requisitos do sistema para AirLLM."""
        requirements = AirLLMBackend.check_requirements()
        
        status_parts = []
        
        if requirements["airllm_installed"]:
            status_parts.append("✅ AirLLM instalado")
        else:
            status_parts.append("❌ AirLLM não instalado (pip install airllm)")
        
        if requirements["torch_installed"]:
            status_parts.append("✅ PyTorch instalado")
        else:
            status_parts.append("❌ PyTorch não instalado")
        
        if requirements["cuda_available"]:
            gpu = requirements["gpu_name"]
            mem = requirements["gpu_memory"]
            status_parts.append(f"✅ GPU: {gpu} ({mem})")
        else:
            status_parts.append("⚠️ CUDA não disponível (CPU apenas)")
        
        self.system_status_label.setText("\n".join(status_parts))
        
        # Cor baseada no status
        if requirements["airllm_installed"] and requirements["torch_installed"]:
            self.system_status_label.setStyleSheet("color: #a6e3a1;")
        else:
            self.system_status_label.setStyleSheet("color: #fab387;")
