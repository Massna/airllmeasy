"""Settings tab."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QFrame, QMessageBox,
    QFileDialog,
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
    """Application settings tab."""
    
    settings_changed = Signal()
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Set up the tab interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # === Download Backend ===
        download_group = QGroupBox("📥 Download Backend")
        download_layout = QVBoxLayout(download_group)
        
        self.backend_group = QButtonGroup(self)
        
        # Option A - Ollama
        ollama_layout = QHBoxLayout()
        self.ollama_radio = QRadioButton("🅰️ Ollama")
        self.ollama_radio.setToolTip("Downloads models from the Ollama registry")
        self.backend_group.addButton(self.ollama_radio)
        ollama_layout.addWidget(self.ollama_radio)
        
        ollama_layout.addWidget(QLabel("URL:"))
        self.ollama_url_input = QLineEdit()
        self.ollama_url_input.setPlaceholderText("http://localhost:11434")
        ollama_layout.addWidget(self.ollama_url_input)
        
        download_layout.addLayout(ollama_layout)
        
        # Option B - LMStudio
        lmstudio_layout = QHBoxLayout()
        self.lmstudio_radio = QRadioButton("🅱️ LMStudio")
        self.lmstudio_radio.setToolTip("Downloads GGUF models from HuggingFace")
        self.backend_group.addButton(self.lmstudio_radio)
        lmstudio_layout.addWidget(self.lmstudio_radio)
        
        lmstudio_layout.addWidget(QLabel("URL:"))
        self.lmstudio_url_input = QLineEdit()
        self.lmstudio_url_input.setPlaceholderText("http://localhost:1234")
        lmstudio_layout.addWidget(self.lmstudio_url_input)
        
        download_layout.addLayout(lmstudio_layout)
        
        layout.addWidget(download_group)
        
        # === AirLLM ===
        airllm_group = QGroupBox("🚀 AirLLM - Optimized Execution")
        airllm_layout = QVBoxLayout(airllm_group)
        
        # Compression
        compression_layout = QHBoxLayout()
        compression_layout.addWidget(QLabel("Compression:"))
        
        self.compression_combo = QComboBox()
        self.compression_combo.addItem("4-bit (Recommended)", "4bit")
        self.compression_combo.addItem("8-bit", "8bit")
        self.compression_combo.addItem("No compression", "none")
        compression_layout.addWidget(self.compression_combo)
        
        compression_layout.addStretch()
        airllm_layout.addLayout(compression_layout)

        # Manual path to airllm package (site-packages)
        path_help = QLabel(
            "If the app can't find AirLLM (import), point to the folder where pip installed the package: "
            "usually the site-packages folder of the same Python/venv where you ran pip install airllm. "
            "You can also select the virtual environment root."
        )
        path_help.setWordWrap(True)
        path_help.setOpenExternalLinks(False)
        airllm_layout.addWidget(path_help)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("AirLLM Folder:"))
        self.airllm_path_input = QLineEdit()
        self.airllm_path_input.setPlaceholderText(
            "E.g.: C:\\…\\venv\\Lib\\site-packages or venv folder"
        )
        self.airllm_path_input.textChanged.connect(self._update_airllm_path_hint)
        path_row.addWidget(self.airllm_path_input, stretch=1)

        self.airllm_browse_btn = QPushButton("📁 Browse…")
        self.airllm_browse_btn.setToolTip("Select folder on disk")
        self.airllm_browse_btn.clicked.connect(self._browse_airllm_folder)
        path_row.addWidget(self.airllm_browse_btn)

        self.airllm_autodetect_btn = QPushButton("🔎 Auto-detect")
        self.airllm_autodetect_btn.setToolTip(
            "Scans all Python/venvs on the system looking for the airllm package"
        )
        self.airllm_autodetect_btn.setStyleSheet("""
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #74c7ec; }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.airllm_autodetect_btn.clicked.connect(self._auto_detect_airllm)
        path_row.addWidget(self.airllm_autodetect_btn)

        self.airllm_clear_path_btn = QPushButton("Clear")
        self.airllm_clear_path_btn.setToolTip("Remove custom path")
        self.airllm_clear_path_btn.clicked.connect(self._clear_airllm_path)
        path_row.addWidget(self.airllm_clear_path_btn)

        airllm_layout.addLayout(path_row)

        self.airllm_path_hint = QLabel()
        self.airllm_path_hint.setWordWrap(True)
        self.airllm_path_hint.setStyleSheet("color: #89b4fa; font-size: 11px;")
        airllm_layout.addWidget(self.airllm_path_hint)
        
        # System status
        req_row = QHBoxLayout()
        self.system_status_btn = QPushButton("🔍 Check System Requirements")
        self.system_status_btn.clicked.connect(self._check_system_requirements)
        req_row.addWidget(self.system_status_btn)

        self.install_airllm_btn = QPushButton("⬇️ Install AirLLM")
        self.install_airllm_btn.setToolTip(
            "Downloads and installs the AirLLM package and dependencies via pip"
        )
        self.install_airllm_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #94e2d5; }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.install_airllm_btn.setVisible(False)  # only shown when not installed
        self.install_airllm_btn.clicked.connect(self._install_airllm_clicked)
        req_row.addWidget(self.install_airllm_btn)

        req_row.addStretch()
        airllm_layout.addLayout(req_row)
        
        self.system_status_label = QLabel()
        self.system_status_label.setWordWrap(True)
        airllm_layout.addWidget(self.system_status_label)
        
        layout.addWidget(airllm_group)
        
        # === Generation Parameters ===
        gen_group = QGroupBox("🎛️ Generation Parameters")
        gen_layout = QVBoxLayout(gen_group)
        
        # Max tokens
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel("Max tokens:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 4096)
        self.max_tokens_spin.setValue(512)
        tokens_layout.addWidget(self.max_tokens_spin)
        tokens_layout.addStretch()
        gen_layout.addLayout(tokens_layout)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        temp_layout.addWidget(self.temperature_spin)
        temp_layout.addWidget(QLabel("(0 = deterministic, 2 = creative)"))
        temp_layout.addStretch()
        gen_layout.addLayout(temp_layout)
        
        layout.addWidget(gen_group)
        
        # === Appearance ===
        appearance_group = QGroupBox("🎨 Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("🌙 Dark", "dark")
        self.theme_combo.addItem("☀️ Light", "light")
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        appearance_layout.addLayout(theme_layout)
        
        layout.addWidget(appearance_group)
        
        # === Action Buttons ===
        buttons_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("🔄 Restore Defaults")
        self.reset_btn.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(self.reset_btn)
        
        buttons_layout.addStretch()
        
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setMinimumWidth(150)
        self.save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
        
        layout.addStretch()
    
    def _load_settings(self):
        """Load current settings."""
        # Backend
        if self.config.download_backend == "ollama":
            self.ollama_radio.setChecked(True)
        else:
            self.lmstudio_radio.setChecked(True)
        
        # URLs
        self.ollama_url_input.setText(self.config.ollama_url)
        self.lmstudio_url_input.setText(self.config.lmstudio_url)
        
        # AirLLM compression
        compression = self.config.airllm_compression
        index = self.compression_combo.findData(compression)
        if index >= 0:
            self.compression_combo.setCurrentIndex(index)

        ap = self.config.airllm_packages_path
        self.airllm_path_input.setText(ap or "")
        self._update_airllm_path_hint()
        
        # Parameters
        self.max_tokens_spin.setValue(self.config.max_tokens)
        self.temperature_spin.setValue(self.config.temperature)
        
        # Theme
        theme = self.config.theme
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
    
    def _save_settings(self):
        """Save settings."""
        # Backend
        if self.ollama_radio.isChecked():
            self.config.download_backend = "ollama"
        else:
            self.config.download_backend = "lmstudio"
        
        # URLs
        self.config.ollama_url = self.ollama_url_input.text().strip() or "http://localhost:11434"
        self.config.lmstudio_url = self.lmstudio_url_input.text().strip() or "http://localhost:1234"
        
        # AirLLM compression
        self.config.airllm_compression = self.compression_combo.currentData()

        self.config.airllm_packages_path = self.airllm_path_input.text().strip() or None
        ok, resolved = set_airllm_packages_path(self.config.airllm_packages_path)
        
        # Parameters
        self.config.max_tokens = self.max_tokens_spin.value()
        self.config.temperature = self.temperature_spin.value()
        
        # Theme
        self.config.theme = self.theme_combo.currentData()
        
        # Save
        if self.config.save():
            self._update_airllm_path_hint()
            msg = "Settings saved successfully!"
            if self.config.airllm_packages_path and not ok:
                msg += (
                    "\n\nWarning: could not confirm the airllm package at this path. "
                    "Check that the folder is the correct site-packages (an airllm subfolder must exist)."
                )
            QMessageBox.information(self, "Success", msg)
            self.settings_changed.emit()
        else:
            QMessageBox.warning(
                self, "Error",
                "Error saving settings!"
            )
    
    def _reset_settings(self):
        """Restore default settings."""
        reply = QMessageBox.question(
            self, "Confirm",
            "Restore all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config.reset()
            self._load_settings()
            set_airllm_packages_path(self.config.airllm_packages_path)
            QMessageBox.information(
                self, "Success",
                "Settings restored!"
            )
    
    def _browse_airllm_folder(self):
        """Open folder selector for AirLLM site-packages / venv."""
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
            self.airllm_path_hint.setText(f"Folder used for import: {resolved}")
        else:
            self.airllm_path_hint.setText(
                "The airllm folder was not found here. Use the site-packages folder of the venv, or the venv root. "
                "If you used pip install -e, select the same site-packages (the app reads .pth files)."
            )

    def _auto_detect_airllm(self):
        """Scan the system for the airllm package and fill the field."""
        self.airllm_autodetect_btn.setEnabled(False)
        self.airllm_autodetect_btn.setText("🔎 Searching…")
        # Force repaint before the operation (may take a few seconds)
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
        """Open AirLLM installation dialog with progress bar."""
        if prompt_install_airllm(parent=self):
            # Installation successful — re-check requirements
            self._check_system_requirements()

    def _check_system_requirements(self):
        """Check system requirements for AirLLM."""
        requirements = AirLLMBackend.check_requirements()
        
        status_parts = []
        
        if requirements["airllm_installed"]:
            status_parts.append("✅ AirLLM installed")
            self.install_airllm_btn.setVisible(False)
        else:
            # Try auto-detection before declaring "not installed"
            detected = auto_detect_airllm_path()
            if detected:
                from ..utils.airllm_import import set_airllm_packages_path as _set_path
                _set_path(detected)
                self.airllm_path_input.setText(detected)
                self._update_airllm_path_hint()
                # Re-check after applying the path
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
        
        # Color based on status
        if requirements["airllm_installed"] and requirements["torch_installed"]:
            self.system_status_label.setStyleSheet("color: #a6e3a1;")
        else:
            self.system_status_label.setStyleSheet("color: #fab387;")
