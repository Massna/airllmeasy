"""Settings tab — premium card-based design."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QFrame, QMessageBox,
    QFileDialog, QScrollArea, QTextEdit, QCheckBox,
)
from PySide6.QtCore import Qt, Signal

from ..utils.config import Config
from ..utils.airllm_import import (
    set_airllm_packages_path,
    resolve_airllm_site_packages,
    auto_detect_airllm_path,
)
from ..backends.airllm_backend import AirLLMBackend
from .install_dialog import prompt_install_airllm


class SettingsTab(QWidget):
    """Application settings tab — premium design."""

    settings_changed = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the tab interface."""
        # Scroll area for all settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 12, 0)

        # === Download Backend ===
        download_group = QGroupBox("  Download Backend")
        download_layout = QVBoxLayout(download_group)
        download_layout.setSpacing(10)

        self.backend_group = QButtonGroup(self)

        # Ollama
        ollama_card = QFrame()
        ollama_card.setObjectName("Card")
        ollama_card_layout = QHBoxLayout(ollama_card)
        ollama_card_layout.setContentsMargins(12, 10, 12, 10)

        self.ollama_radio = QRadioButton("Ollama")
        self.ollama_radio.setToolTip("Downloads models from the Ollama registry")
        self.ollama_radio.setStyleSheet("font-weight: bold;")
        self.backend_group.addButton(self.ollama_radio)
        ollama_card_layout.addWidget(self.ollama_radio)

        url_label1 = QLabel("URL:")
        url_label1.setStyleSheet("color: #6c7086; font-size: 11px;")
        ollama_card_layout.addWidget(url_label1)

        self.ollama_url_input = QLineEdit()
        self.ollama_url_input.setPlaceholderText("http://localhost:11434")
        ollama_card_layout.addWidget(self.ollama_url_input)

        download_layout.addWidget(ollama_card)

        # LMStudio
        lmstudio_card = QFrame()
        lmstudio_card.setObjectName("Card")
        lmstudio_card_layout = QHBoxLayout(lmstudio_card)
        lmstudio_card_layout.setContentsMargins(12, 10, 12, 10)

        self.lmstudio_radio = QRadioButton("LMStudio")
        self.lmstudio_radio.setToolTip("Downloads GGUF models from HuggingFace")
        self.lmstudio_radio.setStyleSheet("font-weight: bold;")
        self.backend_group.addButton(self.lmstudio_radio)
        lmstudio_card_layout.addWidget(self.lmstudio_radio)

        url_label2 = QLabel("URL:")
        url_label2.setStyleSheet("color: #6c7086; font-size: 11px;")
        lmstudio_card_layout.addWidget(url_label2)

        self.lmstudio_url_input = QLineEdit()
        self.lmstudio_url_input.setPlaceholderText("http://localhost:1234")
        lmstudio_card_layout.addWidget(self.lmstudio_url_input)

        download_layout.addWidget(lmstudio_card)

        layout.addWidget(download_group)

        # === AirLLM ===
        airllm_group = QGroupBox("  AirLLM — Optimized Execution")
        airllm_layout = QVBoxLayout(airllm_group)
        airllm_layout.setSpacing(10)

        # Compression
        compression_card = QFrame()
        compression_card.setObjectName("Card")
        compression_layout = QHBoxLayout(compression_card)
        compression_layout.setContentsMargins(12, 10, 12, 10)

        comp_label = QLabel("Compression:")
        comp_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        compression_layout.addWidget(comp_label)

        self.compression_combo = QComboBox()
        self.compression_combo.addItem("4-bit (Recommended)", "4bit")
        self.compression_combo.addItem("8-bit", "8bit")
        self.compression_combo.addItem("No compression", "none")
        compression_layout.addWidget(self.compression_combo)
        compression_layout.addStretch()

        airllm_layout.addWidget(compression_card)

        # Context Size
        ctx_card = QFrame()
        ctx_card.setObjectName("Card")
        ctx_layout = QHBoxLayout(ctx_card)
        ctx_layout.setContentsMargins(12, 10, 12, 10)

        ctx_label = QLabel("Internal Context (n_ctx):")
        ctx_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        ctx_layout.addWidget(ctx_label)

        self.airllm_ctx_spin = QSpinBox()
        self.airllm_ctx_spin.setRange(0, 1048576)
        self.airllm_ctx_spin.setSingleStep(1024)
        self.airllm_ctx_spin.setFixedWidth(80)
        self.airllm_ctx_spin.setStyleSheet("""
            QSpinBox {
                background-color: rgba(15,15,23,0.8);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 6px;
                padding: 4px;
                color: #e0e0ec;
            }
        """)
        ctx_layout.addWidget(self.airllm_ctx_spin)

        ctx_hint = QLabel("0 = Auto (Use model max capacity, uses more RAM)")
        ctx_hint.setStyleSheet("color: #45475a; font-size: 10px;")
        ctx_layout.addWidget(ctx_hint)
        ctx_layout.addStretch()

        airllm_layout.addWidget(ctx_card)

        # Path help
        path_help = QLabel(
            "If the app can't find AirLLM, point to the site-packages folder where pip installed "
            "the package. You can also select the virtual environment root."
        )
        path_help.setWordWrap(True)
        path_help.setStyleSheet("color: #6c7086; font-size: 11px; padding: 4px 8px;")
        airllm_layout.addWidget(path_help)

        # Path row
        path_card = QFrame()
        path_card.setObjectName("Card")
        path_card_layout = QVBoxLayout(path_card)
        path_card_layout.setContentsMargins(12, 10, 12, 10)
        path_card_layout.setSpacing(8)

        path_row = QHBoxLayout()
        path_lbl = QLabel("AirLLM Folder:")
        path_lbl.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        path_row.addWidget(path_lbl)

        self.airllm_path_input = QLineEdit()
        self.airllm_path_input.setPlaceholderText("E.g.: C:\\…\\venv\\Lib\\site-packages")
        self.airllm_path_input.textChanged.connect(self._update_airllm_path_hint)
        path_row.addWidget(self.airllm_path_input, stretch=1)
        path_card_layout.addLayout(path_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.airllm_browse_btn = QPushButton("📁 Browse…")
        self.airllm_browse_btn.setObjectName("GhostBtn")
        self.airllm_browse_btn.setFixedHeight(30)
        self.airllm_browse_btn.clicked.connect(self._browse_airllm_folder)
        btn_row.addWidget(self.airllm_browse_btn)

        self.airllm_autodetect_btn = QPushButton("🔎 Auto-detect")
        self.airllm_autodetect_btn.setFixedHeight(30)
        self.airllm_autodetect_btn.clicked.connect(self._auto_detect_airllm)
        btn_row.addWidget(self.airllm_autodetect_btn)

        self.airllm_clear_path_btn = QPushButton("Clear")
        self.airllm_clear_path_btn.setObjectName("GhostBtn")
        self.airllm_clear_path_btn.setFixedHeight(30)
        self.airllm_clear_path_btn.clicked.connect(self._clear_airllm_path)
        btn_row.addWidget(self.airllm_clear_path_btn)

        btn_row.addStretch()
        path_card_layout.addLayout(btn_row)

        self.airllm_path_hint = QLabel()
        self.airllm_path_hint.setWordWrap(True)
        self.airllm_path_hint.setStyleSheet("color: #89b4fa; font-size: 11px;")
        path_card_layout.addWidget(self.airllm_path_hint)

        airllm_layout.addWidget(path_card)

        # System status
        status_card = QFrame()
        status_card.setObjectName("Card")
        status_card_layout = QVBoxLayout(status_card)
        status_card_layout.setContentsMargins(12, 10, 12, 10)
        status_card_layout.setSpacing(8)

        req_row = QHBoxLayout()
        self.system_status_btn = QPushButton("🔍 Check System Requirements")
        self.system_status_btn.setObjectName("GhostBtn")
        self.system_status_btn.setFixedHeight(32)
        self.system_status_btn.clicked.connect(self._check_system_requirements)
        req_row.addWidget(self.system_status_btn)

        self.install_airllm_btn = QPushButton("⬇️ Install AirLLM")
        self.install_airllm_btn.setObjectName("SuccessBtn")
        self.install_airllm_btn.setFixedHeight(32)
        self.install_airllm_btn.setVisible(False)
        self.install_airllm_btn.clicked.connect(self._install_airllm_clicked)
        req_row.addWidget(self.install_airllm_btn)

        req_row.addStretch()
        status_card_layout.addLayout(req_row)

        self.system_status_label = QLabel()
        self.system_status_label.setWordWrap(True)
        self.system_status_label.setStyleSheet("font-size: 12px;")
        status_card_layout.addWidget(self.system_status_label)

        airllm_layout.addWidget(status_card)

        layout.addWidget(airllm_group)

        # === AI Behavior ===
        ai_group = QGroupBox("  AI Behavior")
        ai_layout = QVBoxLayout(ai_group)
        ai_layout.setSpacing(10)

        # System prompt
        prompt_card = QFrame()
        prompt_card.setObjectName("Card")
        prompt_card_layout = QVBoxLayout(prompt_card)
        prompt_card_layout.setContentsMargins(12, 10, 12, 10)
        prompt_card_layout.setSpacing(8)

        prompt_label = QLabel("System Prompt:")
        prompt_label.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        prompt_card_layout.addWidget(prompt_label)

        self.system_prompt_input = QTextEdit()
        self.system_prompt_input.setMaximumHeight(80)
        self.system_prompt_input.setPlaceholderText("You are a helpful assistant.")
        self.system_prompt_input.setStyleSheet("""
            QTextEdit {
                background-color: rgba(15,15,23,0.6);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        prompt_card_layout.addWidget(self.system_prompt_input)

        # File ops toggle
        self.file_ops_check = QCheckBox("Enable AI file operations (create, edit, move files)")
        self.file_ops_check.setStyleSheet("font-size: 12px;")
        prompt_card_layout.addWidget(self.file_ops_check)

        ai_layout.addWidget(prompt_card)

        layout.addWidget(ai_group)

        # === Generation Parameters ===
        gen_group = QGroupBox("  Generation Parameters")
        gen_layout = QVBoxLayout(gen_group)

        gen_card = QFrame()
        gen_card.setObjectName("Card")
        gen_card_layout = QVBoxLayout(gen_card)
        gen_card_layout.setContentsMargins(12, 10, 12, 10)
        gen_card_layout.setSpacing(10)

        # Max tokens
        tokens_layout = QHBoxLayout()
        tokens_lbl = QLabel("Max tokens:")
        tokens_lbl.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        tokens_layout.addWidget(tokens_lbl)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 4096)
        self.max_tokens_spin.setValue(512)
        self.max_tokens_spin.setFixedWidth(100)
        tokens_layout.addWidget(self.max_tokens_spin)
        tokens_layout.addStretch()
        gen_card_layout.addLayout(tokens_layout)

        # Temperature
        temp_layout = QHBoxLayout()
        temp_lbl = QLabel("Temperature:")
        temp_lbl.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        temp_layout.addWidget(temp_lbl)

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setFixedWidth(80)
        temp_layout.addWidget(self.temperature_spin)

        temp_hint = QLabel("0 = deterministic  •  2 = creative")
        temp_hint.setStyleSheet("color: #45475a; font-size: 10px;")
        temp_layout.addWidget(temp_hint)
        temp_layout.addStretch()
        gen_card_layout.addLayout(temp_layout)

        gen_layout.addWidget(gen_card)

        layout.addWidget(gen_group)

        # === Appearance ===
        appearance_group = QGroupBox(f"  {t('settings.appearance', 'Appearance')}")
        appearance_layout = QVBoxLayout(appearance_group)

        appearance_card = QFrame()
        appearance_card.setObjectName("Card")
        appearance_card_layout = QVBoxLayout(appearance_card)
        appearance_card_layout.setContentsMargins(12, 10, 12, 10)
        appearance_card_layout.setSpacing(10)

        # Theme
        theme_row = QHBoxLayout()
        theme_lbl = QLabel(t("settings.theme", "Theme:"))
        theme_lbl.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        theme_row.addWidget(theme_lbl)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(f"🌙 {t('settings.dark', 'Dark')}", "dark")
        self.theme_combo.addItem(f"☀️ {t('settings.light', 'Light')}", "light")
        self.theme_combo.setFixedWidth(140)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        appearance_card_layout.addLayout(theme_row)

        # Language
        lang_row = QHBoxLayout()
        lang_lbl = QLabel(t("settings.language", "Language:"))
        lang_lbl.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        lang_row.addWidget(lang_lbl)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("🇺🇸 English", "en")
        self.lang_combo.addItem("🇧🇷 Português", "pt")
        self.lang_combo.setFixedWidth(140)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        appearance_card_layout.addLayout(lang_row)

        appearance_layout.addWidget(appearance_card)

        layout.addWidget(appearance_group)

        # === Action Buttons ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.reset_btn = QPushButton(f"🔄  {t('settings.reset', 'Restore Defaults')}")
        self.reset_btn.setObjectName("GhostBtn")
        self.reset_btn.setFixedHeight(38)
        self.reset_btn.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(self.reset_btn)

        buttons_layout.addStretch()

        self.save_btn = QPushButton(f"💾  {t('settings.save', 'Save Settings')}")
        self.save_btn.setMinimumWidth(160)
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #89b4fa, stop:1 #cba6f7);
                color: #0f0f17;
                border-radius: 12px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #b4befe, stop:1 #cba6f7);
            }
        """)
        self.save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self.save_btn)

        layout.addLayout(buttons_layout)

        layout.addStretch()

        scroll.setWidget(scroll_widget)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _load_settings(self):
        """Load current settings."""
        if self.config.download_backend == "ollama":
            self.ollama_radio.setChecked(True)
        else:
            self.lmstudio_radio.setChecked(True)

        self.ollama_url_input.setText(self.config.ollama_url)
        self.lmstudio_url_input.setText(self.config.lmstudio_url)

        compression = self.config.airllm_compression
        index = self.compression_combo.findData(compression)
        if index >= 0:
            self.compression_combo.setCurrentIndex(index)

        self.airllm_ctx_spin.setValue(self.config.airllm_context_size)

        ap = self.config.airllm_packages_path
        self.airllm_path_input.setText(ap or "")
        self._update_airllm_path_hint()

        self.max_tokens_spin.setValue(self.config.max_tokens)
        self.temperature_spin.setValue(self.config.temperature)

        theme = self.config.theme
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        lang = self.config.language
        index = self.lang_combo.findData(lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)

        # AI Behavior
        self.system_prompt_input.setPlainText(self.config.system_prompt)
        self.file_ops_check.setChecked(self.config.file_ops_enabled)

    def _save_settings(self):
        """Save settings."""
        if self.ollama_radio.isChecked():
            self.config.download_backend = "ollama"
        else:
            self.config.download_backend = "lmstudio"

        self.config.ollama_url = self.ollama_url_input.text().strip() or "http://localhost:11434"
        self.config.lmstudio_url = self.lmstudio_url_input.text().strip() or "http://localhost:1234"
        self.config.airllm_compression = self.compression_combo.currentData()
        self.config.airllm_context_size = self.airllm_ctx_spin.value()
        self.config.airllm_packages_path = self.airllm_path_input.text().strip() or None

        ok, resolved = set_airllm_packages_path(self.config.airllm_packages_path)

        self.config.max_tokens = self.max_tokens_spin.value()
        self.config.temperature = self.temperature_spin.value()
        self.config.theme = self.theme_combo.currentData()
        self.config.language = self.lang_combo.currentData()

        # AI Behavior
        self.config.system_prompt = self.system_prompt_input.toPlainText().strip() or "You are a helpful assistant."
        self.config.file_ops_enabled = self.file_ops_check.isChecked()

        if self.config.save():
            self._update_airllm_path_hint()
            msg = t("dialogs.success_msg", "Settings saved successfully!")
            if self.config.airllm_packages_path and not ok:
                msg += (
                    "\n\nWarning: could not confirm the airllm package at this path. "
                    "Check that the folder is the correct site-packages."
                )
            QMessageBox.information(self, t("dialogs.success", "Success"), msg)
            self.settings_changed.emit()
        else:
            QMessageBox.warning(self, t("dialogs.error", "Error"), t("dialogs.error_msg", "Error saving settings!"))

    def _reset_settings(self):
        reply = QMessageBox.question(
            self, "Confirm",
            "Restore all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.config.reset()
            self._load_settings()
            set_airllm_packages_path(self.config.airllm_packages_path)
            QMessageBox.information(self, "Success", "Settings restored!")

    def _browse_airllm_folder(self):
        start = self.airllm_path_input.text().strip() or None
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select the site-packages folder or virtual environment root",
            start or "",
        )
        if folder:
            self.airllm_path_input.setText(folder)
            self._update_airllm_path_hint()

    def _clear_airllm_path(self):
        self.airllm_path_input.clear()
        self._update_airllm_path_hint()

    def _update_airllm_path_hint(self):
        text = self.airllm_path_input.text().strip()
        if not text:
            self.airllm_path_hint.setText("No extra path: using only the Python running the app.")
            return
        resolved = resolve_airllm_site_packages(text)
        if resolved:
            self.airllm_path_hint.setText(f"✅ Folder used for import: {resolved}")
        else:
            self.airllm_path_hint.setText(
                "⚠️ The airllm folder was not found here. Use the site-packages folder of the venv, "
                "or the venv root."
            )

    def _auto_detect_airllm(self):
        self.airllm_autodetect_btn.setEnabled(False)
        self.airllm_autodetect_btn.setText("🔎 Searching…")
        from PySide6.QtWidgets import QApplication as _QApp
        _QApp.processEvents()

        detected = auto_detect_airllm_path()

        self.airllm_autodetect_btn.setEnabled(True)
        self.airllm_autodetect_btn.setText("🔎 Auto-detect")

        if detected:
            self.airllm_path_input.setText(detected)
            self._update_airllm_path_hint()
            QMessageBox.information(
                self, "AirLLM Found",
                f"AirLLM package detected at:\n{detected}\n\n"
                "Click 'Save Settings' to persist.",
            )
        else:
            QMessageBox.warning(
                self, "Not Found",
                "Could not locate the airllm package in any "
                "Python/venv on the system.\n\n"
                "You can:\n"
                "• Install with the '⬇️ Install AirLLM' button\n"
                "• Manually specify the site-packages folder with '📁 Browse…'",
            )

    def _install_airllm_clicked(self):
        if prompt_install_airllm(parent=self):
            self._check_system_requirements()

    def _check_system_requirements(self):
        requirements = AirLLMBackend.check_requirements()

        status_parts = []

        if requirements["airllm_installed"]:
            status_parts.append("✅ AirLLM installed")
            self.install_airllm_btn.setVisible(False)
        else:
            detected = auto_detect_airllm_path()
            if detected:
                from ..utils.airllm_import import set_airllm_packages_path as _set_path
                _set_path(detected)
                self.airllm_path_input.setText(detected)
                self._update_airllm_path_hint()
                requirements = AirLLMBackend.check_requirements()

            if requirements["airllm_installed"]:
                status_parts.append("✅ AirLLM installed (auto-detected)")
                self.install_airllm_btn.setVisible(False)
            else:
                status_parts.append("❌ Could not import the airllm package")
                self.install_airllm_btn.setVisible(True)
                err = requirements.get("airllm_import_error")
                if err:
                    status_parts.append(f"   Error: {err}")
                    el = err.lower()
                    if "optimum" in el and "bettertransformer" in el:
                        status_parts.append(
                            "   → optimum 2.x removed this module. In terminal: "
                            'pip install "optimum>=1.17,<2" "transformers>=4.40,<4.49"'
                        )
                else:
                    status_parts.append(
                        '   Tip: click "⬇️ Install AirLLM" or use "🔎 Auto-detect".'
                    )

        if requirements["torch_installed"]:
            status_parts.append("✅ PyTorch installed")
        else:
            status_parts.append("❌ PyTorch not installed")

        if requirements["cuda_available"]:
            gpu = requirements["gpu_name"]
            mem = requirements["gpu_memory"]
            status_parts.append(f"✅ GPU: {gpu} ({mem})")
        else:
            status_parts.append("⚠️ CUDA not available (CPU only)")

        self.system_status_label.setText("\n".join(status_parts))

        if requirements["airllm_installed"] and requirements["torch_installed"]:
            self.system_status_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
        else:
            self.system_status_label.setStyleSheet("color: #fab387; font-size: 12px;")
