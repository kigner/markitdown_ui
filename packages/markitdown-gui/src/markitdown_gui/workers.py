"""QRunnable conversion tasks + cross-thread signals."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal

from .doc_converter import PowerPointPptConverter, WordDocConverter, WordNotAvailable
from .pipeline import FileJob, ImageMode, build_cli_command


# Markdown image syntax: ![alt](src)  — alt may contain anything but ']',
# src may contain anything but ')'. Multiline blocks (base64 data URIs that
# got line-wrapped) are rare but handled by the DOTALL+non-greedy combo.
_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)", flags=re.DOTALL)


def _strip_images_from_markdown(md_path: str) -> int:
    """Remove every Markdown image reference from `md_path`. Returns count."""
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return 0
    new_text, n = _IMG_RE.subn("", text)
    if n == 0:
        return 0
    # Collapse runs of 3+ blank lines that the image removal may have left behind.
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    return n


class WorkerSignals(QObject):
    """Signals shared by all ConversionTask runnables."""

    started = Signal(int, str)            # (index, src_path)
    finished = Signal(int, str, bool, str)  # (index, src_path, ok, message)
    log = Signal(str)


class ConversionTask(QRunnable):
    """Convert one file via `python -m markitdown` subprocess."""

    def __init__(
        self,
        index: int,
        total: int,
        job: FileJob,
        image_mode: ImageMode,
        signals: WorkerSignals,
    ) -> None:
        super().__init__()
        self._index = index
        self._total = total
        self._job = job
        self._image_mode = image_mode
        self._signals = signals
        # Avoid Qt's "delete after run" so the C++ side won't double-free in tests.
        self.setAutoDelete(True)

    def _emit_log(self, msg: str) -> None:
        self._signals.log.emit(msg)

    def run(self) -> None:  # noqa: D401 — Qt expects this name
        job = self._job
        self._signals.started.emit(self._index, job.src_path)

        os.makedirs(os.path.dirname(job.md_path) or ".", exist_ok=True)
        if self._image_mode == ImageMode.EXTRACT:
            os.makedirs(job.images_dir, exist_ok=True)

        tmp_converted: Optional[str] = None
        src_override: Optional[str] = None

        try:
            if job.is_legacy_doc:
                try:
                    tmp_converted = WordDocConverter.instance().convert(job.src_path)
                    src_override = tmp_converted
                except WordNotAvailable as e:
                    self._signals.finished.emit(
                        self._index, job.src_path, False, f"Word not available: {e}"
                    )
                    return
                except Exception as e:  # pragma: no cover -- COM failures
                    self._signals.finished.emit(
                        self._index, job.src_path, False, f".doc -> .docx failed: {e}"
                    )
                    return
            elif job.is_legacy_ppt:
                try:
                    tmp_converted = PowerPointPptConverter.instance().convert(
                        job.src_path
                    )
                    src_override = tmp_converted
                except WordNotAvailable as e:
                    self._signals.finished.emit(
                        self._index, job.src_path, False,
                        f"PowerPoint not available: {e}",
                    )
                    return
                except Exception as e:  # pragma: no cover -- COM failures
                    self._signals.finished.emit(
                        self._index, job.src_path, False, f".ppt -> .pptx failed: {e}"
                    )
                    return

            argv = build_cli_command(
                job=job,
                image_mode=self._image_mode,
                src_override=src_override,
            )

            try:
                proc = subprocess.run(
                    argv,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
            except FileNotFoundError as e:
                self._signals.finished.emit(
                    self._index, job.src_path, False, f"subprocess failed: {e}"
                )
                return

            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()
                self._signals.finished.emit(
                    self._index, job.src_path, False, err or f"exit {proc.returncode}"
                )
                return

            # IGNORE mode: markitdown has no native "drop all images" flag, so
            # the default conversion still emits broken/placeholder image refs
            # (truncated data URIs from DOCX, fake .jpg links from PPTX, etc.).
            # Strip them here so the output is pure text.
            if self._image_mode == ImageMode.IGNORE:
                _strip_images_from_markdown(job.md_path)

            self._signals.finished.emit(self._index, job.src_path, True, "")
        finally:
            if tmp_converted:
                tmp_dir = os.path.dirname(tmp_converted)
                shutil.rmtree(tmp_dir, ignore_errors=True)
