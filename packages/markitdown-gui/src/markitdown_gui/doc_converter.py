"""Legacy Office binary -> OOXML conversion via COM automation.

Handles:
  * .doc  -> .docx  (Microsoft Word)
  * .ppt  -> .pptx  (Microsoft PowerPoint)

Windows-only. Both Word.Application and PowerPoint.Application are STA
(single-threaded apartment); a shared instance cannot be called safely
from worker threads, so each conversion spins up its own Office app
inside the calling thread's apartment and quits it.
"""

from __future__ import annotations

import os
import sys
import tempfile
from typing import Optional


_WD_FORMAT_DOCX = 16  # wdFormatXMLDocument
_PP_SAVE_AS_OPEN_XML_PRESENTATION = 24  # ppSaveAsOpenXMLPresentation


class WordNotAvailable(RuntimeError):
    pass


class WordDocConverter:
    """Stateless helper. `instance()` is provided only to keep call sites short."""

    _instance: Optional["WordDocConverter"] = None

    @classmethod
    def instance(cls) -> "WordDocConverter":
        if cls._instance is None:
            cls._instance = WordDocConverter()
        return cls._instance

    @staticmethod
    def is_available() -> bool:
        """Return True if Word can be launched on this machine."""
        if sys.platform != "win32":
            return False
        try:
            import pythoncom  # noqa: F401
            import win32com.client  # noqa: F401
        except ImportError:
            return False
        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            try:
                app = win32com.client.DispatchEx("Word.Application")
                try:
                    app.Visible = False
                finally:
                    app.Quit()
            finally:
                pythoncom.CoUninitialize()
            return True
        except Exception:
            return False

    def convert(self, doc_path: str) -> str:
        """Convert `doc_path` (.doc) to a temporary .docx and return its path.

        Caller is responsible for deleting the temp dir of the result.
        Raises WordNotAvailable if Word can't be launched.
        """
        if sys.platform != "win32":
            raise WordNotAvailable("Word COM is only available on Windows.")

        try:
            import pythoncom
            import win32com.client
        except ImportError as e:
            raise WordNotAvailable(f"pywin32 not installed: {e}")

        tmp_dir = tempfile.mkdtemp(prefix="mdgui_doc_")
        base = os.path.splitext(os.path.basename(doc_path))[0]
        out_path = os.path.join(tmp_dir, f"{base}.docx")

        # COM is STA: every thread that talks to Word must own its own Word
        # object and CoInitialize/Uninitialize bracket. A shared singleton +
        # lock does NOT work — worker threads other than the one that built
        # the instance get RPC_E_WRONG_THREAD when calling methods on it.
        pythoncom.CoInitialize()
        try:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0  # wdAlertsNone
            try:
                doc = word.Documents.Open(
                    os.path.abspath(doc_path),
                    ConfirmConversions=False,
                    ReadOnly=True,
                    AddToRecentFiles=False,
                )
                try:
                    doc.SaveAs2(out_path, FileFormat=_WD_FORMAT_DOCX)
                finally:
                    doc.Close(SaveChanges=False)
            finally:
                word.Quit()
        finally:
            pythoncom.CoUninitialize()

        return out_path

    def shutdown(self) -> None:
        """Kept for API compatibility; nothing persistent to tear down anymore."""
        return None


class PowerPointPptConverter:
    """Convert legacy .ppt files to .pptx via Microsoft PowerPoint COM."""

    _instance: Optional["PowerPointPptConverter"] = None

    @classmethod
    def instance(cls) -> "PowerPointPptConverter":
        if cls._instance is None:
            cls._instance = PowerPointPptConverter()
        return cls._instance

    @staticmethod
    def is_available() -> bool:
        if sys.platform != "win32":
            return False
        try:
            import pythoncom  # noqa: F401
            import win32com.client  # noqa: F401
        except ImportError:
            return False
        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            try:
                app = win32com.client.DispatchEx("PowerPoint.Application")
                try:
                    # PowerPoint refuses to launch fully hidden on some
                    # versions; Visible=False during Quit is fine though.
                    app.Quit()
                except Exception:
                    pass
            finally:
                pythoncom.CoUninitialize()
            return True
        except Exception:
            return False

    def convert(self, ppt_path: str) -> str:
        """Convert `ppt_path` (.ppt) to a temporary .pptx and return its path.

        Caller is responsible for deleting the temp dir of the result.
        Raises WordNotAvailable (reused) if PowerPoint can't be launched.
        """
        if sys.platform != "win32":
            raise WordNotAvailable("PowerPoint COM is only available on Windows.")

        try:
            import pythoncom
            import win32com.client
        except ImportError as e:
            raise WordNotAvailable(f"pywin32 not installed: {e}")

        tmp_dir = tempfile.mkdtemp(prefix="mdgui_ppt_")
        base = os.path.splitext(os.path.basename(ppt_path))[0]
        out_path = os.path.join(tmp_dir, f"{base}.pptx")

        pythoncom.CoInitialize()
        try:
            ppt = win32com.client.DispatchEx("PowerPoint.Application")
            # PowerPoint Application has no Visible property settable to False
            # on older versions, so don't try. Open with WithWindow=False keeps
            # it offscreen.
            try:
                pres = ppt.Presentations.Open(
                    os.path.abspath(ppt_path),
                    ReadOnly=True,
                    Untitled=False,
                    WithWindow=False,
                )
                try:
                    pres.SaveAs(out_path, _PP_SAVE_AS_OPEN_XML_PRESENTATION)
                finally:
                    pres.Close()
            finally:
                ppt.Quit()
        finally:
            pythoncom.CoUninitialize()

        return out_path
