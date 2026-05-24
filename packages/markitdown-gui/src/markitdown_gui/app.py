"""QApplication bootstrap + stylesheet loader."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .settings_dialog import GuiSettings


_RES = Path(__file__).resolve().parent / "resources"


def _load_qss(theme: str) -> str:
    name = "styles_dark.qss" if theme == "dark" else "styles_light.qss"
    path = _RES / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("MarkItDown")
    app.setOrganizationName("MarkItDown")

    settings = GuiSettings()

    def apply_theme(theme: str) -> None:
        qss = _load_qss(theme)
        app.setStyleSheet(qss)

    apply_theme(settings.theme)

    win = MainWindow(theme_setter=apply_theme)
    win.show()
    return app.exec()
