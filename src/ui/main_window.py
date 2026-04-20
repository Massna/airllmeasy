"""Main application window — premium modern design."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QStatusBar, QLabel, QPushButton, QMessageBox, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QAction, QIcon, QFont, QColor

from .download_tab import DownloadTab
from .chat_tab import ChatTab
from .settings_tab import SettingsTab
from .extensions_tab import ExtensionsTab
from ..utils.config import Config
from src.utils.extensions import ExtensionManager
from src.utils.i18n import t


# ─────────────────────────────────── Theme ────────────────────────────────────

DARK_THEME = """
/* ─── Global ─── */
QMainWindow, QWidget {
    background-color: #0f0f17;
    color: #e0e0ec;
    font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
}

/* ─── Top bar ─── */
#TopBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #161625, stop:1 #1a1a2e);
    border-bottom: 1px solid rgba(139,180,250,0.08);
    min-height: 52px;
}

/* ─── Sidebar ─── */
#Sidebar {
    background-color: #12121e;
    border-right: 1px solid rgba(255,255,255,0.04);
    min-width: 90px;
    max-width: 90px;
}
#Sidebar QPushButton {
    background: transparent;
    border: none;
    border-radius: 12px;
    padding: 10px;
    margin: 4px 6px;
    font-size: 22px;
    font-weight: normal;
    color: #b4befe;
}
#Sidebar QPushButton:hover {
    background-color: rgba(139,180,250,0.1);
    color: #89b4fa;
}
#Sidebar QPushButton:checked, #Sidebar QPushButton[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(139,180,250,0.18), stop:1 rgba(180,190,254,0.12));
    color: #89b4fa;
    border-left: 2px solid #89b4fa;
    border-radius: 0px 12px 12px 0px;
}

/* ─── Content area ─── */
#ContentStack {
    background-color: transparent;
}

/* ─── Tab widget ─── */
QTabWidget::pane {
    border: none;
    background-color: transparent;
    margin-top: -1px;
}
QTabBar {
    background: transparent;
}
QTabBar::tab {
    background-color: transparent;
    color: #6c7086;
    padding: 10px 22px;
    margin: 0 1px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    color: #b4befe;
    background-color: rgba(139,180,250,0.05);
}

/* ─── Cards / GroupBox ─── */
QGroupBox {
    background-color: rgba(22,22,37,0.7);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    margin-top: 16px;
    padding: 18px 16px 14px 16px;
    font-size: 13px;
    font-weight: bold;
    color: #b4befe;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 18px;
    padding: 0 8px;
    color: #89b4fa;
}

/* ─── Buttons ─── */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #89b4fa, stop:1 #b4befe);
    color: #0f0f17;
    border: none;
    padding: 9px 20px;
    border-radius: 10px;
    font-weight: bold;
    font-size: 12px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #b4befe, stop:1 #cba6f7);
}
QPushButton:pressed {
    background-color: #74c7ec;
}
QPushButton:disabled {
    background-color: #1e1e2e;
    color: #45475a;
}
QPushButton#DangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f38ba8, stop:1 #eba0ac);
}
QPushButton#DangerBtn:hover {
    background: #f38ba8;
}
QPushButton#GhostBtn {
    background: transparent;
    color: #89b4fa;
    border: 1px solid rgba(139,180,250,0.3);
}
QPushButton#GhostBtn:hover {
    background-color: rgba(139,180,250,0.1);
    border-color: #89b4fa;
}
QPushButton#SuccessBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #a6e3a1, stop:1 #94e2d5);
    color: #0f0f17;
}
QPushButton#SuccessBtn:hover {
    background: #94e2d5;
}

/* ─── Inputs ─── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: rgba(22,22,37,0.85);
    color: #e0e0ec;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: rgba(139,180,250,0.25);
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid rgba(139,180,250,0.45);
    background-color: rgba(22,22,37,0.95);
}

/* ─── ComboBox ─── */
QComboBox {
    background-color: rgba(22,22,37,0.85);
    color: #e0e0ec;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 20px;
}
QComboBox:hover { border-color: rgba(139,180,250,0.3); }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox::down-arrow { image: none; border: none; }
QComboBox QAbstractItemView {
    background-color: #161625;
    color: #e0e0ec;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 4px;
    selection-background-color: rgba(139,180,250,0.2);
}

/* ─── List widget ─── */
QListWidget {
    background-color: rgba(22,22,37,0.7);
    color: #e0e0ec;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    border-radius: 8px;
    padding: 8px 12px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(139,180,250,0.2), stop:1 rgba(180,190,254,0.1));
    color: #89b4fa;
}
QListWidget::item:hover:!selected {
    background-color: rgba(255,255,255,0.03);
}

/* ─── Progress bar ─── */
QProgressBar {
    background-color: rgba(22,22,37,0.8);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    text-align: center;
    color: #e0e0ec;
    font-weight: bold;
    min-height: 24px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #89b4fa, stop:1 #b4befe);
    border-radius: 7px;
}

/* ─── Scrollbar ─── */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
    margin: 4px 0;
}
QScrollBar::handle:vertical {
    background-color: rgba(255,255,255,0.12);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: rgba(139,180,250,0.35);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background-color: rgba(255,255,255,0.12);
    border-radius: 4px;
    min-width: 30px;
}

/* ─── Labels ─── */
QLabel { color: #e0e0ec; }
QLabel#Subtitle { color: #6c7086; font-size: 11px; }
QLabel#Accent { color: #89b4fa; font-weight: bold; }

/* ─── SpinBox ─── */
QSpinBox, QDoubleSpinBox {
    background-color: rgba(22,22,37,0.85);
    color: #e0e0ec;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: rgba(139,180,250,0.4);
}

/* ─── Radio buttons ─── */
QRadioButton {
    color: #e0e0ec;
    spacing: 8px;
    font-size: 13px;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #45475a;
    background-color: transparent;
}
QRadioButton::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QRadioButton::indicator:hover {
    border-color: rgba(139,180,250,0.5);
}

/* ─── Checkbox ─── */
QCheckBox {
    color: #e0e0ec;
    spacing: 8px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #45475a;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* ─── Splitter ─── */
QSplitter::handle {
    background-color: rgba(255,255,255,0.04);
}
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical { height: 2px; }

/* ─── Menu bar ─── */
QMenuBar {
    background-color: transparent;
    color: #6c7086;
    border: none;
    font-size: 12px;
    padding: 2px 6px;
}
QMenuBar::item { padding: 6px 12px; border-radius: 6px; }
QMenuBar::item:selected { background-color: rgba(139,180,250,0.1); color: #89b4fa; }

QMenu {
    background-color: #161625;
    color: #e0e0ec;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 8px 30px 8px 20px; border-radius: 6px; }
QMenu::item:selected { background-color: rgba(139,180,250,0.15); color: #89b4fa; }
QMenu::separator { background-color: rgba(255,255,255,0.06); height: 1px; margin: 4px 8px; }

/* ─── Status bar ─── */
QStatusBar {
    background-color: #0a0a12;
    color: #6c7086;
    font-size: 11px;
    border-top: 1px solid rgba(255,255,255,0.04);
    padding: 2px 12px;
}

/* ─── Tooltip ─── */
QToolTip {
    background-color: #1e1e30;
    color: #e0e0ec;
    border: 1px solid rgba(139,180,250,0.2);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ─── Frame cards ─── */
QFrame#Card {
    background-color: rgba(22,22,37,0.6);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 14px;
    padding: 14px;
}
"""


class MainWindow(QMainWindow):
    """Main window of the AirLLMEasy — premium glass design."""

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setWindowTitle(t("app.name", "AirLLMEasy"))
        self.setMinimumSize(1000, 650)

        # Restore saved geometry
        geometry = self.config.get("window_geometry")
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))
        else:
            self.resize(1120, 760)

        # Extensions
        self.extension_mgr = ExtensionManager(self.config)
        self.extension_mgr.load_all(self)

        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._apply_theme()

    # ─────────────────────────── UI Construction ───────────────────────────

    def _setup_ui(self):
        """Set up the main interface with sidebar + content layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top bar ──
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(56)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(18, 0, 18, 0)
        top_bar_layout.setSpacing(12)

        # Logo area
        logo_label = QLabel("⚡")
        logo_label.setStyleSheet("font-size: 22px; padding-right: 4px;")
        top_bar_layout.addWidget(logo_label)

        title_label = QLabel(t("app.name", "AirLLMEasy"))
        title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; "
            "background: transparent; "
            "color: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
            "stop:0 #89b4fa, stop:1 #cba6f7);"
        )
        top_bar_layout.addWidget(title_label)

        # Backend badge
        self.backend_badge = QLabel()
        self.backend_badge.setObjectName("BackendBadge")
        self._update_backend_badge()
        top_bar_layout.addWidget(self.backend_badge)

        top_bar_layout.addStretch()

        # Quick backend switch buttons
        self.ollama_quick_btn = QPushButton(t("download.ollama", "Ollama"))
        self.ollama_quick_btn.setObjectName("GhostBtn")
        self.ollama_quick_btn.setFixedHeight(32)
        self.ollama_quick_btn.clicked.connect(lambda: self._switch_backend("ollama"))
        top_bar_layout.addWidget(self.ollama_quick_btn)

        self.lmstudio_quick_btn = QPushButton(t("download.lmstudio", "LMStudio"))
        self.lmstudio_quick_btn.setObjectName("GhostBtn")
        self.lmstudio_quick_btn.setFixedHeight(32)
        self.lmstudio_quick_btn.clicked.connect(lambda: self._switch_backend("lmstudio"))
        top_bar_layout.addWidget(self.lmstudio_quick_btn)

        root_layout.addWidget(top_bar)

        # ── Body: sidebar + content ──
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(2)

        self._sidebar_buttons = []
        sidebar_items = [
            ("📥", t("sidebar.download", "Download"), 0),
            ("💬", t("sidebar.chat", "Chat"), 1),
            ("🧩", t("sidebar.extensions", "Extensions"), 2),
            ("⚙️", t("sidebar.settings", "Settings"), 3),
        ]
        
        for icon, tooltip, idx in sidebar_items:
            btn = QPushButton(icon)
            btn.setFixedSize(60, 48)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._on_sidebar_click(i))
            sidebar_layout.addWidget(btn, alignment=Qt.AlignCenter)
            self._sidebar_buttons.append(btn)

        sidebar_layout.addStretch()

        # About button at bottom
        about_btn = QPushButton("ℹ️")
        about_btn.setFixedSize(60, 48)
        about_btn.setToolTip(t("sidebar.about", "About"))
        about_btn.clicked.connect(self._show_about)
        sidebar_layout.addWidget(about_btn, alignment=Qt.AlignCenter)

        body.addWidget(sidebar)

        # Content area
        content_area = QWidget()
        content_area.setObjectName("ContentStack")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(16, 12, 16, 8)
        content_layout.setSpacing(0)

        # Main tabs (hidden tab bar — sidebar controls navigation)
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBar().setVisible(False)

        # Download Tab
        self.download_tab = DownloadTab(self.config)
        self.tab_widget.addTab(self.download_tab, t("sidebar.download", "Download"))

        # Chat Tab
        self.chat_tab = ChatTab(self.config, self.extension_mgr)
        self.tab_widget.addTab(self.chat_tab, t("sidebar.chat", "Chat"))

        # Extensions Tab
        self.extensions_tab = ExtensionsTab(self.config, self.extension_mgr)
        self.tab_widget.addTab(self.extensions_tab, t("sidebar.extensions", "Extensions"))

        # Settings Tab
        self.settings_tab = SettingsTab(self.config)
        self.settings_tab.settings_changed.connect(self._on_settings_changed)
        self.tab_widget.addTab(self.settings_tab, t("sidebar.settings", "Settings"))

        content_layout.addWidget(self.tab_widget)

        body.addWidget(content_area, stretch=1)

        root_layout.addLayout(body)

        # Default: Chat tab selected
        self._on_sidebar_click(1)

    def _setup_menu(self):
        """Set up the application menu."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu(t("menu.file", "&File"))

        refresh_action = QAction(t("menu.refresh", "&Refresh List"), self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_models)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        exit_action = QAction(t("menu.exit", "&Exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        backend_menu = menubar.addMenu(t("menu.backend", "&Backend"))

        ollama_action = QAction(t("menu.use_ollama", "Use &Ollama"), self)
        ollama_action.triggered.connect(lambda: self._switch_backend("ollama"))
        backend_menu.addAction(ollama_action)

        lmstudio_action = QAction(t("menu.use_lmstudio", "Use &LMStudio"), self)
        lmstudio_action.triggered.connect(lambda: self._switch_backend("lmstudio"))
        backend_menu.addAction(lmstudio_action)

        help_menu = menubar.addMenu(t("menu.help", "&Help"))

        about_action = QAction(t("menu.about", "&About"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_statusbar(self):
        """Set up the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage(f"{t('app.ready', 'Ready')}  •  {t('app.name', 'AirLLMEasy')} {t('app.version', 'v1.0')}")

    # ─────────────────────────── Theme ────────────────────────────────────

    def _apply_theme(self):
        """Apply the selected theme."""
        if self.config.theme == "dark":
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet("")  # System default

    # ─────────────────────────── Sidebar ──────────────────────────────────

    def _on_sidebar_click(self, index: int):
        """Switch the active tab via sidebar."""
        for i, btn in enumerate(self._sidebar_buttons):
            btn.setProperty("active", i == index)
            btn.setChecked(i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.tab_widget.setCurrentIndex(index)

    def _retranslate_ui(self):
        """Update UI texts with current language."""
        self.setWindowTitle(t("app.name", "AirLLMEasy"))
        
        # Sidebar buttons
        sidebar_keys = [
            "sidebar.download", "sidebar.chat", 
            "sidebar.extensions", "sidebar.settings"
        ]
        sidebar_defaults = ["Download", "Chat", "Extensions", "Settings"]
        
        for i, btn in enumerate(self._sidebar_buttons):
            if i < len(sidebar_keys):
                btn.setText(f"  {t(sidebar_keys[i], sidebar_defaults[i])}")
                
        # Tab titles (though they are hidden, keep them synced)
        for i in range(len(sidebar_keys)):
            self.tab_widget.setTabText(i, t(sidebar_keys[i], sidebar_defaults[i]))

        # Menu and Statusbar
        # (Menu is harder to update live without recreation, but let's do status bar)
        self._setup_statusbar()
        self._update_backend_badge()

        # Update tabs
        if hasattr(self, "download_tab"):
            self.download_tab.retranslateUi()
        if hasattr(self, "settings_tab"):
            self.settings_tab.retranslateUi()
        # Add ExtensionsTab if I implement it

    # ─────────────────────────── Backend badge ────────────────────────────

    def _update_backend_badge(self):
        """Update the current backend badge."""
        backend = self.config.download_backend
        if backend == "ollama":
            text = f"● {t('download.ollama', 'Ollama')}"
            color = "#a6e3a1"
        else:
            text = f"● {t('download.lmstudio', 'LMStudio')}"
            color = "#89b4fa"

        self.backend_badge.setText(text)
        self.backend_badge.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                font-weight: bold;
                color: {color};
                padding: 4px 12px;
                background-color: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
            }}
        """)

    # ─────────────────────────── Actions ──────────────────────────────────

    def _switch_backend(self, backend: str):
        """Switch between backends."""
        self.config.download_backend = backend
        self.config.save()
        self._update_backend_badge()
        self.download_tab.refresh_for_backend()
        self.statusbar.showMessage(f"Backend changed to {backend.title()}")

    def _refresh_models(self):
        """Refresh the model list."""
        self.download_tab.refresh_models()
        self.statusbar.showMessage(t("menu.refresh", "Model list updated"))

    def _on_settings_changed(self):
        """Called when settings change."""
        from src.utils.i18n import load_language
        load_language(self.config.language)
        
        self._retranslate_ui()
        self._apply_theme()
        self.download_tab.refresh_for_backend()

    def _show_about(self):
        """Show the About dialog."""
        QMessageBox.about(
            self,
            t("dialogs.about_title", "About AirLLMEasy"),
            f"""<div style="text-align:center">
            <h2 style="color:#89b4fa">⚡ {t('app.name', 'AirLLMEasy')}</h2>
            <p style="color:#6c7086">Version 1.0.0</p>
            <br>
            <br>
            <p><b>Supported backends:</b></p>
            <ul style="text-align:left">
                <li>🟢 Ollama — Download and execution</li>
                <li>🔵 LMStudio — Download and execution</li>
                <li>🚀 AirLLM — Memory-optimized execution</li>
            </ul>
            <br>
            <p><b>Features:</b></p>
            <ul style="text-align:left">
                <li>📁 AI-powered file management (create, edit, move)</li>
                <li>💬 Streaming chat with all backends</li>
                <li>📥 One-click model downloads</li>
            </ul>
            </div>"""
        )

    def closeEvent(self, event):
        """Save state on close."""
        self.config.set("window_geometry", self.saveGeometry().toHex().data().decode())
        self.config.save()
        event.accept()
