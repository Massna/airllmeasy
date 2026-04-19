"""Dependency installation dialog with animated progress bar.

Works both in normal execution (python main.py) and in a bundled
executable created with PyInstaller (.exe). When running as .exe,
after installation the dialog automatically configures the package path
so the app can import airllm.
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
    """Modal dialog that installs packages via pip, showing real-time progress.

    Usage::

        dlg = InstallDialog(
            packages=["airllm>=2.8.0", "optimum>=1.17,<2", "transformers>=4.40,<4.49"],
            title="Install AirLLM",
            description="The AirLLM package was not found. Do you want to install it now?",
            parent=parent_widget,
        )
        if dlg.exec() == QDialog.Accepted:
            # Packages installed successfully
            ...
    """

    def __init__(
        self,
        packages: List[str],
        *,
        title: str = "Install Dependencies",
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

        # Icon + title
        header = QHBoxLayout()
        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet("font-size: 32px;")
        header.addWidget(icon_lbl)

        title_lbl = QLabel(self.windowTitle())
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title_lbl)
        header.addStretch()
        root.addLayout(header)

        # Description
        desc_text = description
        if is_frozen():
            desc_text += (
                "\n\n🔧 Running as .exe — the system-installed Python will be "
                "used to download the packages."
            )

        if desc_text:
            desc = QLabel(desc_text)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #a6adc8; font-size: 13px; margin-bottom: 4px;")
            root.addWidget(desc)

        # Package list
        pkg_text = ", ".join(self.packages)
        pkg_lbl = QLabel(f"<b>Packages:</b> {pkg_text}")
        pkg_lbl.setWordWrap(True)
        pkg_lbl.setStyleSheet("font-size: 12px;")
        root.addWidget(pkg_lbl)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Waiting…")
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

        # Detailed status label
        self.status_label = QLabel("Ready to install.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #bac2de; font-size: 12px;")
        root.addWidget(self.status_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)

        self.install_btn = QPushButton("⬇️ Install Now")
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
    # Installation logic
    # ------------------------------------------------------------------
    def _start_install(self):
        self._installing = True
        self.install_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setFormat("Starting…")
        self.status_label.setText("Starting pip install…")

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
            # indeterminate
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setFormat("Downloading…")
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(pct)
            self.progress_bar.setFormat(f"{pct}%")

    def _on_site_packages(self, path: str):
        """Received from worker: site-packages where pip installed the packages.

        When running as .exe, we need to add this path to sys.path
        and configure airllm_import so that imports work.
        """
        self._installed_site_packages = path

        if is_frozen() and path:
            # Add to sys.path immediately
            if path not in sys.path:
                sys.path.insert(0, path)
            importlib.invalidate_caches()
            # Configure in airllm_import for runtime persistence
            set_airllm_packages_path(path)

    def _on_finished(self, ok: bool, message: str):
        self._installing = False
        self.progress_bar.setRange(0, 100)

        if ok:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("✅ Complete!")
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

            # Extra message when running as .exe
            final_msg = message
            if is_frozen() and self._installed_site_packages:
                final_msg += f"\n📂 Packages at: {self._installed_site_packages}"

            self.status_label.setText(final_msg)
            self.status_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
            self.cancel_btn.setText("Close")

            if self._on_success:
                self._on_success()

            # Auto-close after 1.5s
            QTimer.singleShot(1500, self.accept)
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("❌ Failed")
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
            self.install_btn.setText("🔄 Try Again")

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
        """Path of the site-packages where packages were installed (or None)."""
        return self._installed_site_packages


# ---------------------------------------------------------------------------
# Quick-use helpers
# ---------------------------------------------------------------------------

def prompt_install_airllm(parent: Optional[QWidget] = None) -> bool:
    """Show dialog to install AirLLM + dependencies. Returns True if installed."""
    dlg = InstallDialog(
        packages=[
            "airllm>=2.8.0",
            "optimum>=1.17.0,<2.0.0",
            "transformers>=4.40.0,<4.49.0",
            "huggingface_hub>=0.20.0",
        ],
        title="Install AirLLM",
        description=(
            "The AirLLM package was not found in the current Python environment.\n"
            "Do you want to download and install it now? (Requires internet connection)"
        ),
        parent=parent,
    )
    result = dlg.exec() == QDialog.Accepted

    # If running as .exe and installed, save the path to config
    if result and is_frozen() and dlg.installed_site_packages:
        _save_site_packages_to_config(dlg.installed_site_packages)

    return result


def prompt_install_llama_cpp(parent: Optional[QWidget] = None) -> bool:
    """Show dialog to install llama-cpp-python. Returns True if installed."""
    dlg = InstallDialog(
        packages=["llama-cpp-python>=0.2.0"],
        title="Install llama-cpp-python",
        description=(
            "The llama-cpp-python package is required to run GGUF models.\n"
            "Do you want to download and install it now? (Requires internet connection)\n\n"
            "⚠️ Compilation may take a few minutes."
        ),
        parent=parent,
    )
    result = dlg.exec() == QDialog.Accepted

    if result and is_frozen() and dlg.installed_site_packages:
        _save_site_packages_to_config(dlg.installed_site_packages)

    return result


def _save_site_packages_to_config(site_packages_path: str):
    """Save the site-packages path to config for future .exe runs."""
    try:
        from ..utils.config import Config
        config = Config()
        config.airllm_packages_path = site_packages_path
        config.save()
    except Exception:
        pass  # Better not to fail because of config
