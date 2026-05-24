"""Main window: input/output pickers, image-mode radios, start button, log area."""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import QSize, Qt, QThreadPool, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .doc_converter import PowerPointPptConverter, WordDocConverter
from .i18n import LanguageManager, tr
from .pipeline import FileJob, ImageMode, InputMode, Plan, plan
from .settings_dialog import GuiSettings, SettingsDialog
from .workers import ConversionTask, WorkerSignals


class MainWindow(QMainWindow):
    def __init__(self, theme_setter) -> None:
        """`theme_setter(name: str)` is a callback that applies a QSS theme to the
        whole QApplication. Provided by app.py.
        """
        super().__init__()
        self._theme_setter = theme_setter
        self._settings = GuiSettings()
        self._lang = LanguageManager.instance()
        self._lang.set_language(self._settings.language)

        self._input_paths: List[str] = []
        self._input_mode: InputMode = InputMode.BATCH

        self._pool = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(self._settings.threads)
        self._signals = WorkerSignals()
        self._signals.started.connect(self._on_task_started)
        self._signals.finished.connect(self._on_task_finished)
        self._signals.log.connect(self._append_log)

        self._total = 0
        self._completed = 0
        self._succeeded = 0
        self._failed = 0

        self._build_ui()
        self._lang.language_changed.connect(self._retranslate)
        self._retranslate()

    # -- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        self.setMinimumSize(QSize(820, 560))
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # Row: Select Input  + path field
        row_in = QHBoxLayout()
        row_in.setSpacing(10)
        self._btn_input = QPushButton()
        self._btn_input.setFixedWidth(180)
        self._btn_input.clicked.connect(self._choose_input)
        self._input_path_edit = QLineEdit()
        self._input_path_edit.setReadOnly(True)
        row_in.addWidget(self._btn_input)
        row_in.addWidget(self._input_path_edit, stretch=1)
        root.addLayout(row_in)

        # Row: Select Output + path field
        row_out = QHBoxLayout()
        row_out.setSpacing(10)
        self._btn_output = QPushButton()
        self._btn_output.setFixedWidth(180)
        self._btn_output.clicked.connect(self._choose_output)
        self._output_path_edit = QLineEdit()
        self._output_path_edit.setReadOnly(True)
        row_out.addWidget(self._btn_output)
        row_out.addWidget(self._output_path_edit, stretch=1)
        root.addLayout(row_out)

        # Row: Image-handling radios
        row_img = QHBoxLayout()
        row_img.setSpacing(14)
        self._lbl_image = QLabel()
        self._lbl_image.setObjectName("sectionLabel")
        row_img.addWidget(self._lbl_image)

        self._radio_extract = QRadioButton()
        self._radio_embed = QRadioButton()
        self._radio_ignore = QRadioButton()
        self._image_group = QButtonGroup(self)
        self._image_group.addButton(self._radio_extract, 0)
        self._image_group.addButton(self._radio_embed, 1)
        self._image_group.addButton(self._radio_ignore, 2)
        self._radio_extract.setChecked(True)

        row_img.addWidget(self._radio_extract)
        row_img.addWidget(self._radio_embed)
        row_img.addWidget(self._radio_ignore)
        row_img.addStretch(1)
        root.addLayout(row_img)

        # Row: Settings (wrench) + Start
        row_start = QHBoxLayout()
        row_start.setSpacing(10)
        self._btn_settings = QPushButton("⚙")  # gear unicode (works without icon assets)
        self._btn_settings.setObjectName("settingsButton")
        self._btn_settings.setFixedWidth(48)
        self._btn_settings.setToolTip(tr("btn.settings"))
        self._btn_settings.clicked.connect(self._open_settings)

        self._btn_start = QPushButton()
        self._btn_start.setObjectName("startButton")
        self._btn_start.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_start.clicked.connect(self._start_processing)

        row_start.addWidget(self._btn_settings)
        row_start.addWidget(self._btn_start, stretch=1)
        root.addLayout(row_start)

        # Log area
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._log, stretch=1)

    # -- i18n -------------------------------------------------------------

    @Slot()
    def _retranslate(self) -> None:
        self.setWindowTitle(tr("app.title"))
        self._btn_input.setText(tr("btn.select_input"))
        self._btn_output.setText(tr("btn.select_output"))
        self._btn_start.setText(tr("btn.start"))
        self._btn_settings.setToolTip(tr("btn.settings"))
        self._input_path_edit.setPlaceholderText(tr("placeholder.input"))
        self._output_path_edit.setPlaceholderText(tr("placeholder.output"))
        self._lbl_image.setText(tr("label.image_handling"))
        self._radio_extract.setText(tr("opt.extract"))
        self._radio_embed.setText(tr("opt.embed"))
        self._radio_ignore.setText(tr("opt.ignore"))

    # -- Helpers ----------------------------------------------------------

    def _append_log(self, msg: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{stamp}] {msg}")

    def _current_image_mode(self) -> ImageMode:
        if self._radio_embed.isChecked():
            return ImageMode.EMBED
        if self._radio_ignore.isChecked():
            return ImageMode.IGNORE
        return ImageMode.EXTRACT

    # -- Input picker -----------------------------------------------------

    def _choose_input(self) -> None:
        menu = QMenu(self)
        act_folder = menu.addAction(tr("dialog.input.folder"))
        act_files = menu.addAction(tr("dialog.input.files"))
        chosen = menu.exec_(self._btn_input.mapToGlobal(self._btn_input.rect().bottomLeft()))
        if chosen is act_folder:
            folder = QFileDialog.getExistingDirectory(self, tr("dialog.choose_folder"))
            if folder:
                self._input_paths = [folder]
                self._input_mode = InputMode.BATCH
                self._input_path_edit.setText(folder)
        elif chosen is act_files:
            files, _ = QFileDialog.getOpenFileNames(self, tr("dialog.choose_files"))
            if files:
                self._input_paths = files
                self._input_mode = InputMode.SINGLE_OR_MULTI
                if len(files) == 1:
                    self._input_path_edit.setText(files[0])
                else:
                    self._input_path_edit.setText(f"{len(files)} files: {files[0]} ...")

    def _choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("dialog.choose_folder"))
        if folder:
            self._output_path_edit.setText(folder)

    # -- Settings ---------------------------------------------------------

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, parent=self)
        # PySide6 6.11 dropped per-instance enum attributes (`dlg.Accepted`
        # raises AttributeError, swallowed by the event loop). Use the class
        # enum and compare against the int returned by exec().
        if dlg.exec() != int(QDialog.DialogCode.Accepted):
            return

        lang = dlg.selected_language()
        if lang != self._settings.language:
            self._settings.language = lang
            self._lang.set_language(lang)

        threads = dlg.selected_threads()
        if threads != self._settings.threads:
            self._settings.threads = threads
            self._pool.setMaxThreadCount(threads)

        theme = dlg.selected_theme()
        if theme != self._settings.theme:
            self._settings.theme = theme
            self._theme_setter(theme)

    # -- Start ------------------------------------------------------------

    def _start_processing(self) -> None:
        if not self._input_paths:
            self._append_log(tr("log.no_input"))
            return
        output_dir = self._output_path_edit.text().strip()
        if not output_dir:
            self._append_log(tr("log.no_output"))
            return

        try:
            the_plan: Plan = plan(self._input_paths, self._input_mode, output_dir)
        except Exception as e:
            self._append_log(f"Error planning: {e}")
            return

        os.makedirs(the_plan.output_root, exist_ok=True)

        self._append_log(tr("log.output_dir", path=the_plan.output_root))
        for sk in the_plan.skipped_unsupported:
            self._append_log(tr("log.skipped_unsupported", path=sk))

        # Handle legacy .doc availability check up-front.
        if the_plan.legacy_doc_count > 0:
            if not WordDocConverter.is_available():
                self._append_log(
                    tr("log.no_word_installed", n=the_plan.legacy_doc_count)
                )
                the_plan.jobs = [j for j in the_plan.jobs if not j.is_legacy_doc]

        # Handle legacy .ppt availability check up-front.
        if the_plan.legacy_ppt_count > 0:
            if not PowerPointPptConverter.is_available():
                self._append_log(
                    tr("log.no_powerpoint_installed", n=the_plan.legacy_ppt_count)
                )
                the_plan.jobs = [j for j in the_plan.jobs if not j.is_legacy_ppt]

        if not the_plan.jobs:
            self._append_log(tr("log.scanned", n=0))
            return

        self._append_log(tr("log.scanned", n=len(the_plan.jobs)))
        self._append_log(tr("log.start", threads=self._settings.threads))

        # Reset counters and dispatch.
        self._total = len(the_plan.jobs)
        self._completed = 0
        self._succeeded = 0
        self._failed = 0
        self._btn_start.setEnabled(False)

        image_mode = self._current_image_mode()

        for i, job in enumerate(the_plan.jobs, start=1):
            if job.is_legacy_doc:
                self._append_log(
                    tr("log.doc_converting", name=os.path.basename(job.src_path))
                )
            elif job.is_legacy_ppt:
                self._append_log(
                    tr("log.ppt_converting", name=os.path.basename(job.src_path))
                )
            task = ConversionTask(
                index=i,
                total=self._total,
                job=job,
                image_mode=image_mode,
                signals=self._signals,
            )
            self._pool.start(task)

    @Slot(int, str)
    def _on_task_started(self, index: int, src_path: str) -> None:
        self._append_log(
            tr(
                "log.start_file",
                i=index,
                n=self._total,
                name=os.path.basename(src_path),
            )
        )

    @Slot(int, str, bool, str)
    def _on_task_finished(self, index: int, src_path: str, ok: bool, msg: str) -> None:
        self._completed += 1
        if ok:
            self._succeeded += 1
            self._append_log(
                tr(
                    "log.done_file",
                    i=index,
                    n=self._total,
                    name=os.path.basename(src_path),
                )
            )
        else:
            self._failed += 1
            self._append_log(
                tr(
                    "log.error_file",
                    i=index,
                    n=self._total,
                    name=os.path.basename(src_path),
                    err=msg,
                )
            )
        if self._completed >= self._total:
            self._append_log(
                tr("log.all_done", ok=self._succeeded, failed=self._failed)
            )
            self._btn_start.setEnabled(True)

    # -- Close ------------------------------------------------------------

    def closeEvent(self, event) -> None:
        # Best-effort shutdown of Word COM if it was used.
        try:
            WordDocConverter.instance().shutdown()
        except Exception:
            pass
        super().closeEvent(event)
