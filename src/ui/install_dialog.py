"""Diálogo de instalação de dependências com barra de progresso animada.

Funciona tanto em execução normal (python main.py) quanto em executável
empacotado com PyInstaller (.exe).  Quando rodando como .exe, após a
instalação o diálogo configura automaticamente o caminho dos pacotes
para que o app consiga importar o airllm.
"""
from __future__ import annotations

import importlib
import sys
from typing import Callable, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..utils.pip_installer import PipInstallWorker, is_frozen
from ..utils.airllm_import import set_airllm_packages_path


class InstallDialog(QDialog):
    """Diálogo modal que instala pacotes via pip, mostrando progresso em tempo real.

    Uso::

        dlg = InstallDialog(
            packages=["airllm>=2.8.0", "optimum>=1.17,<2", "transformers>=4.40,<4.49"],
            title="Instalar AirLLM",
            description="O pacote AirLLM não foi encontrado. Deseja instalar agora?",
            parent=parent_widget,
        )
        if dlg.exec() == QDialog.Accepted:
            # Pacotes instalados com sucesso
            ...
    """

    def __init__(
        self,
        packages: List[str],
        *,
        title: str = "Instalar Dependências",
        description: str = "",
        extra_pip_args: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
        on_success: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.packages = packages
        self._extra_pip_args = extra_pip_args or []
        self._on_success = on_success
        self._worker: Optional[PipInstallWorker] = None
        self._installing = False
        self._installed_site_packages: Optional[str] = None

        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )

        self._build_ui(description)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self, description: str):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        # Ícone + título
        header = QHBoxLayout()
        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header.addWidget(icon_lbl)

        title_lbl = QLabel(self.windowTitle())
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title_lbl)
        header.addStretch()
        root.addLayout(header)

        # Descrição
        desc_text = description
        if is_frozen():
            desc_text += (
                "\n\n🔧 Executando como .exe — será usado o Python instalado "
                "no sistema para baixar os pacotes."
            )

        if desc_text:
            desc = QLabel(desc_text)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #a6adc8; font-size: 13px; margin-bottom: 4px;")
            root.addWidget(desc)

        # Lista de pacotes
        pkg_text = ", ".join(self.packages)
        pkg_lbl = QLabel(f"<b>Pacotes:</b> {pkg_text}")
        pkg_lbl.setWordWrap(True)
        pkg_lbl.setStyleSheet("font-size: 12px;")
        root.addWidget(pkg_lbl)

        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Aguardando…")
        self.progress_bar.setMinimumHeight(28)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                text-align: center;
                color: #cdd6f4;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #74c7ec, stop:1 #89b4fa
                );
                border-radius: 5px;
            }
            """
        )
        root.addWidget(self.progress_bar)

        # Label de status detalhado
        self.status_label = QLabel("Pronto para instalar.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #bac2de; font-size: 12px;")
        root.addWidget(self.status_label)

        # Botões
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)

        self.install_btn = QPushButton("⬇️ Instalar Agora")
        self.install_btn.setMinimumWidth(140)
        self.install_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #94e2d5; }
            QPushButton:pressed { background-color: #74c7ec; }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
            """
        )
        self.install_btn.clicked.connect(self._start_install)
        btn_row.addWidget(self.install_btn)

        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Lógica de instalação
    # ------------------------------------------------------------------
    def _start_install(self):
        self._installing = True
        self.install_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)  # indeterminada
        self.progress_bar.setFormat("Iniciando…")
        self.status_label.setText("Iniciando pip install…")

        self._worker = PipInstallWorker(
            self.packages,
            extra_args=self._extra_pip_args,
            label=", ".join(self.packages),
            parent=self,
        )
        self._worker.progress_text.connect(self._on_progress_text)
        self._worker.progress_pct.connect(self._on_progress_pct)
        self._worker.site_packages.connect(self._on_site_packages)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.start()

    def _on_progress_text(self, text: str):
        self.status_label.setText(text)

    def _on_progress_pct(self, pct: int):
        if pct < 0:
            # indeterminada
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("Baixando…")
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(pct)
            self.progress_bar.setFormat(f"{pct}%")

    def _on_site_packages(self, path: str):
        """Recebido do worker: site-packages onde pip instalou os pacotes.

        Quando rodando como .exe, precisamos adicionar esse caminho ao sys.path
        e configurar no airllm_import para que imports funcionem.
        """
        self._installed_site_packages = path

        if is_frozen() and path:
            # Adiciona ao sys.path imediatamente
            if path not in sys.path:
                sys.path.insert(0, path)
            importlib.invalidate_caches()
            # Configura no airllm_import para persistência do runtime
            set_airllm_packages_path(path)

    def _on_finished(self, ok: bool, message: str):
        self._installing = False
        self.progress_bar.setRange(0, 100)

        if ok:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("✅ Concluído!")
            self.progress_bar.setStyleSheet(
                """
                QProgressBar {
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 6px;
                    text-align: center;
                    color: #a6e3a1;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #a6e3a1, stop:1 #94e2d5
                    );
                    border-radius: 5px;
                }
                """
            )

            # Mensagem extra quando rodando como .exe
            final_msg = message
            if is_frozen() and self._installed_site_packages:
                final_msg += f"\n📂 Pacotes em: {self._installed_site_packages}"

            self.status_label.setText(final_msg)
            self.status_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
            self.cancel_btn.setText("Fechar")

            if self._on_success:
                self._on_success()

            # Fecha automaticamente depois de 1.5s
            QTimer.singleShot(1500, self.accept)
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("❌ Falha")
            self.progress_bar.setStyleSheet(
                """
                QProgressBar {
                    background-color: #313244;
                    border: 1px solid #f38ba8;
                    border-radius: 6px;
                    text-align: center;
                    color: #f38ba8;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: #f38ba8;
                    border-radius: 5px;
                }
                """
            )
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #f38ba8; font-size: 12px;")
            self.install_btn.setEnabled(True)
            self.install_btn.setText("🔄 Tentar Novamente")

    def _on_cancel(self):
        if self._installing and self._worker:
            self._worker.cancel()
            self._worker.wait(3000)
        self.reject()

    def closeEvent(self, event):
        if self._installing and self._worker:
            self._worker.cancel()
            self._worker.wait(3000)
        event.accept()

    @property
    def installed_site_packages(self) -> Optional[str]:
        """Caminho do site-packages onde os pacotes foram instalados (ou None)."""
        return self._installed_site_packages


# ---------------------------------------------------------------------------
# Helpers para uso rápido
# ---------------------------------------------------------------------------

def prompt_install_airllm(parent: Optional[QWidget] = None) -> bool:
    """Mostra diálogo para instalar AirLLM + dependências. Retorna True se instalou."""
    dlg = InstallDialog(
        packages=[
            "airllm>=2.8.0",
            "optimum>=1.17.0,<2.0.0",
            "transformers>=4.40.0,<4.49.0",
            "huggingface_hub>=0.20.0",
        ],
        title="Instalar AirLLM",
        description=(
            "O pacote AirLLM não foi encontrado no ambiente Python atual.\n"
            "Deseja baixar e instalar agora? (Requer conexão com a internet)"
        ),
        parent=parent,
    )
    result = dlg.exec() == QDialog.Accepted

    # Se rodando como .exe e instalou, salva o caminho na config
    if result and is_frozen() and dlg.installed_site_packages:
        _save_site_packages_to_config(dlg.installed_site_packages)

    return result


def prompt_install_llama_cpp(parent: Optional[QWidget] = None) -> bool:
    """Mostra diálogo para instalar llama-cpp-python. Retorna True se instalou."""
    dlg = InstallDialog(
        packages=["llama-cpp-python>=0.2.0"],
        title="Instalar llama-cpp-python",
        description=(
            "O pacote llama-cpp-python é necessário para executar modelos GGUF.\n"
            "Deseja baixar e instalar agora? (Requer conexão com a internet)\n\n"
            "⚠️ A compilação pode demorar alguns minutos."
        ),
        parent=parent,
    )
    result = dlg.exec() == QDialog.Accepted

    if result and is_frozen() and dlg.installed_site_packages:
        _save_site_packages_to_config(dlg.installed_site_packages)

    return result


def _save_site_packages_to_config(site_packages_path: str):
    """Salva o caminho do site-packages na config para próximas execuções do .exe."""
    try:
        from ..utils.config import Config
        config = Config()
        config.airllm_packages_path = site_packages_path
        config.save()
    except Exception:
        pass  # Melhor não falhar por causa de config
