from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QListWidgetItem, QPushButton, QFrame,
    QTextBrowser, QFileDialog
)
from PySide6.QtCore import Qt
import os
import sys
import shutil
from pathlib import Path
import subprocess

from ..utils.config import Config
from ..utils.extensions import ExtensionManager

class ExtensionsTab(QWidget):
    """Tab to view and manage extensions."""

    def __init__(self, config: Config, extension_mgr: ExtensionManager):
        super().__init__()
        self.config = config
        self.extension_mgr = extension_mgr
        self._setup_ui()
        self._load_extensions()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        # ── Left column: Extensions List ──
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        
        header_row = QHBoxLayout()
        header = QLabel(f"🧩 {t('extensions.loaded', 'Loaded Extensions')}")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #cdd6f4;")
        header_row.addWidget(header)
        header_row.addStretch()

        # Add Extension Button
        self.add_ext_btn = QPushButton(f"➕ {t('extensions.add', 'Add Plugin')}")
        self.add_ext_btn.setObjectName("PrimaryBtn")
        self.add_ext_btn.clicked.connect(self._add_extension)
        header_row.addWidget(self.add_ext_btn)

        # Open Folder Button
        self.open_folder_btn = QPushButton(f"📂 {t('extensions.folder', 'Folder')}")
        self.open_folder_btn.setObjectName("GhostBtn")
        self.open_folder_btn.setToolTip(t("extensions.open_folder_tip", "Open the extensions folder"))
        self.open_folder_btn.clicked.connect(self._open_extensions_folder)
        header_row.addWidget(self.open_folder_btn)

        # Refresh
        self.refresh_btn = QPushButton(f"🔃 {t('chat.refresh', 'Reload')}")
        self.refresh_btn.setObjectName("GhostBtn")
        self.refresh_btn.clicked.connect(self._reload_extensions)
        header_row.addWidget(self.refresh_btn)

        left_col.addLayout(header_row)

        desc = QLabel(t("extensions.desc", "Add .py scripts to the extensions folder to grant AirLLM new abilities!"))
        desc.setStyleSheet("color: #a6adc8; font-size: 14px; margin-bottom: 8px;")
        left_col.addWidget(desc)

        self.ext_list = QListWidget()
        self.ext_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(30, 30, 46, 0.6);
                border-radius: 12px;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 6px;
                background-color: rgba(49, 50, 68, 0.4);
            }
            QListWidget::item:selected {
                background-color: rgba(137, 180, 250, 0.2);
                border: 1px solid #89b4fa;
            }
        """)
        self.ext_list.itemSelectionChanged.connect(self._on_selection_changed)
        left_col.addWidget(self.ext_list)

        # ── Right column: Details ──
        right_col = QVBoxLayout()
        
        details_card = QFrame()
        details_card.setObjectName("Card")
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(24, 24, 24, 24)
        details_layout.setSpacing(16)

        self.detail_title = QLabel("Select an extension")
        self.detail_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        details_layout.addWidget(self.detail_title)

        self.detail_meta = QLabel("")
        self.detail_meta.setStyleSheet("color: #9399b2; font-size: 13px; font-style: italic;")
        details_layout.addWidget(self.detail_meta)

        self.detail_desc = QTextBrowser()
        self.detail_desc.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: #bac2de;
                font-size: 14px;
            }
        """)
        details_layout.addWidget(self.detail_desc)

        # Show Ai Tools Box
        self.tools_label = QLabel("Available AI Tools:")
        self.tools_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #89b4fa; margin-top: 10px;")
        self.tools_label.setVisible(False)
        details_layout.addWidget(self.tools_label)

        self.tools_display = QTextBrowser()
        self.tools_display.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(17,17,27, 0.7);
                border-radius: 8px;
                padding: 10px;
                color: #a6e3a1;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        self.tools_display.setMaximumHeight(150)
        self.tools_display.setVisible(False)
        details_layout.addWidget(self.tools_display)

        right_col.addWidget(details_card)

        # Add columns to main layout
        layout.addLayout(left_col, stretch=2)
        layout.addLayout(right_col, stretch=3)

    def _load_extensions(self):
        self.ext_list.clear()
        
        for name, ext in self.extension_mgr.extensions.items():
            item = QListWidgetItem(f"🧩 {name}")
            item.setData(Qt.UserRole, ext)
            self.ext_list.addItem(item)
            
        if self.ext_list.count() > 0:
            self.ext_list.setCurrentRow(0)
        else:
            self._clear_details()

    def _reload_extensions(self):
        # We need a reference to the main window to pass as context
        # But we can just use self.parent() or pass None since Most simple tools don't need app context
        app_context = self.window()
        self.extension_mgr.extensions.clear()
        self.extension_mgr.load_all(app_context)
        self._load_extensions()

    def _open_extensions_folder(self):
        folder = str(self.extension_mgr.extensions_dir)
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _add_extension(self):
        """Allows user to select a .py file and copies it to the extensions dir."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Python Plugin Files",
            "",
            "Python Files (*.py)"
        )
        
        if files:
            added = False
            for f in files:
                src_path = Path(f)
                dest_path = self.extension_mgr.extensions_dir / src_path.name
                
                # Prevent copying over itself if same file
                if src_path.resolve() != dest_path.resolve():
                    shutil.copy2(src_path, dest_path)
                    added = True
            
            if added:
                self._reload_extensions()

    def _on_selection_changed(self):
        current = self.ext_list.currentItem()
        if not current:
            self._clear_details()
            return

        ext = current.data(Qt.UserRole)
        self.detail_title.setText(ext.name)
        self.detail_meta.setText(f"Version {ext.version} • by {ext.author}")
        self.detail_desc.setText(ext.description)

        # Tools
        tools = ext.get_ai_tools()
        if tools:
            self.tools_label.setVisible(True)
            self.tools_display.setVisible(True)
            tools_html = ""
            for t in tools:
                tools_html += f"<b>{t.get('name', 'unknown')}</b>: {t.get('description', '')}<br><br>"
            self.tools_display.setHtml(tools_html)
        else:
            self.tools_label.setVisible(False)
            self.tools_display.setVisible(False)

    def _clear_details(self):
        self.detail_title.setText("Select an extension")
        self.detail_meta.setText("")
        self.detail_desc.setText("")
        self.tools_label.setVisible(False)
        self.tools_display.setVisible(False)
