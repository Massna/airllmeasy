"""Janela principal da aplicação."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QStatusBar, QMenuBar, QMenu, QToolBar, QLabel, QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon

from .download_tab import DownloadTab
from .chat_tab import ChatTab
from .settings_tab import SettingsTab
from ..utils.config import Config


class MainWindow(QMainWindow):
    """Janela principal do AI Local Manager."""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setWindowTitle("AI Local Manager")
        self.setMinimumSize(900, 600)
        
        # Restaura geometria salva
        geometry = self.config.get("window_geometry")
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))
        else:
            self.resize(1000, 700)
        
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._apply_theme()
    
    def _setup_ui(self):
        """Configura a interface principal."""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header com info do backend atual
        header = QHBoxLayout()
        self.backend_label = QLabel()
        self._update_backend_label()
        header.addWidget(self.backend_label)
        header.addStretch()
        main_layout.addLayout(header)
        
        # Abas principais
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        # Aba de Download
        self.download_tab = DownloadTab(self.config)
        self.tab_widget.addTab(self.download_tab, "📥 Download de Modelos")
        
        # Aba de Chat
        self.chat_tab = ChatTab(self.config)
        self.tab_widget.addTab(self.chat_tab, "💬 Chat")
        
        # Aba de Configurações
        self.settings_tab = SettingsTab(self.config)
        self.settings_tab.settings_changed.connect(self._on_settings_changed)
        self.tab_widget.addTab(self.settings_tab, "⚙️ Configurações")
        
        main_layout.addWidget(self.tab_widget)
    
    def _setup_menu(self):
        """Configura o menu da aplicação."""
        menubar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menubar.addMenu("&Arquivo")
        
        refresh_action = QAction("&Atualizar Lista", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_models)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Sair", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Backend
        backend_menu = menubar.addMenu("&Backend")
        
        ollama_action = QAction("Usar &Ollama (A)", self)
        ollama_action.triggered.connect(lambda: self._switch_backend("ollama"))
        backend_menu.addAction(ollama_action)
        
        lmstudio_action = QAction("Usar &LMStudio (B)", self)
        lmstudio_action.triggered.connect(lambda: self._switch_backend("lmstudio"))
        backend_menu.addAction(lmstudio_action)
        
        # Menu Ajuda
        help_menu = menubar.addMenu("A&juda")
        
        about_action = QAction("&Sobre", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Configura a barra de status."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Pronto")
    
    def _apply_theme(self):
        """Aplica o tema selecionado."""
        if self.config.theme == "dark":
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                }
                QTabWidget::pane {
                    border: 1px solid #45475a;
                    background-color: #1e1e2e;
                    border-radius: 4px;
                }
                QTabBar::tab {
                    background-color: #313244;
                    color: #cdd6f4;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background-color: #45475a;
                }
                QTabBar::tab:hover {
                    background-color: #585b70;
                }
                QPushButton {
                    background-color: #89b4fa;
                    color: #1e1e2e;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #b4befe;
                }
                QPushButton:pressed {
                    background-color: #74c7ec;
                }
                QPushButton:disabled {
                    background-color: #45475a;
                    color: #6c7086;
                }
                QLineEdit, QTextEdit, QPlainTextEdit {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 6px;
                }
                QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                    border-color: #89b4fa;
                }
                QComboBox {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 6px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox QAbstractItemView {
                    background-color: #313244;
                    color: #cdd6f4;
                    selection-background-color: #45475a;
                }
                QListWidget {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                }
                QListWidget::item:selected {
                    background-color: #45475a;
                }
                QListWidget::item:hover {
                    background-color: #3b3d4d;
                }
                QProgressBar {
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    text-align: center;
                    color: #cdd6f4;
                }
                QProgressBar::chunk {
                    background-color: #89b4fa;
                    border-radius: 3px;
                }
                QScrollBar:vertical {
                    background-color: #313244;
                    width: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background-color: #45475a;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #585b70;
                }
                QLabel {
                    color: #cdd6f4;
                }
                QMenuBar {
                    background-color: #1e1e2e;
                    color: #cdd6f4;
                }
                QMenuBar::item:selected {
                    background-color: #45475a;
                }
                QMenu {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                }
                QMenu::item:selected {
                    background-color: #45475a;
                }
                QStatusBar {
                    background-color: #181825;
                    color: #a6adc8;
                }
                QGroupBox {
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: #cdd6f4;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QSlider::groove:horizontal {
                    background-color: #313244;
                    height: 6px;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background-color: #89b4fa;
                    width: 16px;
                    height: 16px;
                    margin: -5px 0;
                    border-radius: 8px;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
        else:
            self.setStyleSheet("")  # Tema claro padrão do sistema
    
    def _update_backend_label(self):
        """Atualiza o label do backend atual."""
        backend = self.config.download_backend
        if backend == "ollama":
            text = "🅰️ Backend: Ollama"
            color = "#a6e3a1"
        else:
            text = "🅱️ Backend: LMStudio"
            color = "#89b4fa"
        
        self.backend_label.setText(text)
        self.backend_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {color};
                padding: 4px 8px;
                background-color: rgba(255,255,255,0.05);
                border-radius: 4px;
            }}
        """)
    
    def _switch_backend(self, backend: str):
        """Alterna entre backends."""
        self.config.download_backend = backend
        self.config.save()
        self._update_backend_label()
        self.download_tab.refresh_for_backend()
        self.statusbar.showMessage(f"Backend alterado para {backend.upper()}")
    
    def _refresh_models(self):
        """Atualiza a lista de modelos."""
        self.download_tab.refresh_models()
        self.statusbar.showMessage("Lista de modelos atualizada")
    
    def _on_settings_changed(self):
        """Chamado quando as configurações mudam."""
        self._update_backend_label()
        self._apply_theme()
        self.download_tab.refresh_for_backend()
    
    def _show_about(self):
        """Mostra diálogo Sobre."""
        QMessageBox.about(
            self,
            "Sobre AI Local Manager",
            """<h2>AI Local Manager</h2>
            <p>Versão 1.0.0</p>
            <p>Gerencie e execute modelos de IA localmente.</p>
            <br>
            <p><b>Backends suportados:</b></p>
            <ul>
                <li>🅰️ Ollama - Download e execução</li>
                <li>🅱️ LMStudio - Download e execução</li>
                <li>🚀 AirLLM - Execução otimizada para pouca memória</li>
            </ul>
            """
        )
    
    def closeEvent(self, event):
        """Salva estado ao fechar."""
        # Salva geometria da janela
        self.config.set("window_geometry", self.saveGeometry().toHex().data().decode())
        self.config.save()
        event.accept()
