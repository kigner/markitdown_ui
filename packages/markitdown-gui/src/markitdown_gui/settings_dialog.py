"""Settings dialog for the wrench icon: language / threads / plugins / theme."""

from __future__ import annotations

import os

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
)

from .i18n import LanguageManager, tr


LANG_LABELS = {"en": "English", "zh": "中文"}
THEME_KEYS = ["dark", "light"]


def default_thread_count() -> int:
    return max(1, min(4, (os.cpu_count() or 4)))


class GuiSettings:
    """Thin wrapper around QSettings with typed accessors + defaults."""

    ORG = "MarkItDown"
    APP = "GUI"

    def __init__(self) -> None:
        self._s = QSettings(self.ORG, self.APP)

    @property
    def language(self) -> str:
        return str(self._s.value("language", "en"))

    @language.setter
    def language(self, v: str) -> None:
        self._s.setValue("language", v)

    @property
    def threads(self) -> int:
        try:
            return int(self._s.value("threads", default_thread_count()))
        except (TypeError, ValueError):
            return default_thread_count()

    @threads.setter
    def threads(self, v: int) -> None:
        self._s.setValue("threads", int(v))

    @property
    def theme(self) -> str:
        return str(self._s.value("theme", "dark"))

    @theme.setter
    def theme(self, v: str) -> None:
        self._s.setValue("theme", v)


class SettingsDialog(QDialog):
    def __init__(self, settings: GuiSettings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings

        self.setWindowTitle(tr("dialog.settings.title"))
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        layout.addLayout(form)

        # Language
        self._lang_combo = QComboBox()
        for code in LanguageManager.instance().available():
            self._lang_combo.addItem(LANG_LABELS.get(code, code), userData=code)
        self._select_combo_data(self._lang_combo, settings.language)
        form.addRow(tr("dialog.settings.language"), self._lang_combo)

        # Threads
        self._threads_spin = QSpinBox()
        self._threads_spin.setRange(1, 16)
        self._threads_spin.setValue(settings.threads)
        form.addRow(tr("dialog.settings.threads"), self._threads_spin)

        # Theme
        self._theme_combo = QComboBox()
        self._theme_combo.addItem(tr("theme.dark"), userData="dark")
        self._theme_combo.addItem(tr("theme.light"), userData="light")
        self._select_combo_data(self._theme_combo, settings.theme)
        form.addRow(tr("dialog.settings.theme"), self._theme_combo)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _select_combo_data(combo: QComboBox, data: str) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return

    def selected_language(self) -> str:
        return str(self._lang_combo.currentData())

    def selected_theme(self) -> str:
        return str(self._theme_combo.currentData())

    def selected_threads(self) -> int:
        return int(self._threads_spin.value())
