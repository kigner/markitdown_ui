import sys
import io
import os
import re
from warnings import warn

from typing import BinaryIO, Any

from ._html_converter import HtmlConverter
from ..converter_utils.docx.pre_process import pre_process_docx
from .._base_converter import DocumentConverterResult
from .._stream_info import StreamInfo
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE

# Try loading optional (but in this case, required) dependencies
# Save reporting of any exceptions for later
_dependency_exc_info = None
try:
    import mammoth

except ImportError:
    # Preserve the error and stack trace for later
    _dependency_exc_info = sys.exc_info()


ACCEPTED_MIME_TYPE_PREFIXES = [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

ACCEPTED_FILE_EXTENSIONS = [".docx"]


# Heuristics for spotting altText that's actually an author's local filesystem
# path (commonly leaked by QQ/Tencent paste-into-Word, where the temp cache
# path ends up as the image's descr). We treat anything matching this as junk
# and clear the alt attribute.
_PATH_LIKE_PATTERNS = [
    re.compile(r"^[a-zA-Z]:[\\/]"),       # C:\... / C:/...
    re.compile(r"^\\\\"),                  # UNC \\server\share
    re.compile(r"^/[a-zA-Z0-9_.\-]+/"),    # Unix abs path
    re.compile(r"^~/"),                    # User home
]


def _looks_like_local_path(text: str) -> bool:
    if not text:
        return False
    s = text.strip()
    if any(p.match(s) for p in _PATH_LIKE_PATTERNS):
        return True
    # Also: anything that's mostly path separators and ends in a common image
    # extension is almost certainly junk altText, not a real caption.
    if (s.count("\\") >= 2 or s.count("/") >= 2) and re.search(
        r"\.(jpg|jpeg|png|gif|bmp|tiff|webp|emf|wmf)$", s, re.IGNORECASE
    ):
        return True
    return False


class DocxConverter(HtmlConverter):
    """
    Converts DOCX files to Markdown. Style information (e.g.m headings) and tables are preserved where possible.
    """

    def __init__(self):
        super().__init__()
        self._html_converter = HtmlConverter()

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,  # Options to pass to the converter
    ) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()

        if extension in ACCEPTED_FILE_EXTENSIONS:
            return True

        for prefix in ACCEPTED_MIME_TYPE_PREFIXES:
            if mimetype.startswith(prefix):
                return True

        return False

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,  # Options to pass to the converter
    ) -> DocumentConverterResult:
        # Check: the dependencies
        if _dependency_exc_info is not None:
            raise MissingDependencyException(
                MISSING_DEPENDENCY_MESSAGE.format(
                    converter=type(self).__name__,
                    extension=".docx",
                    feature="docx",
                )
            ) from _dependency_exc_info[
                1
            ].with_traceback(  # type: ignore[union-attr]
                _dependency_exc_info[2]
            )

        style_map = kwargs.get("style_map", None)
        pre_process_stream = pre_process_docx(file_stream)

        # Build mammoth options
        mammoth_options = {}
        if style_map is not None:
            mammoth_options["style_map"] = style_map

        if kwargs.get("extract_images", False):
            images_dir = kwargs.get("images_dir")
            if images_dir:
                from ..converter_utils._image_extractor import ImageExtractor

                rel_prefix = os.path.basename(images_dir)
                name_prefix = kwargs.get("image_name_prefix", "")
                extractor = ImageExtractor(
                    images_dir, rel_prefix=rel_prefix, name_prefix=name_prefix
                )

                def save_image_to_disk(image):
                    try:
                        with image.open() as image_source:
                            blob = image_source.read()
                        filename = extractor.save_image(
                            blob,
                            content_type=image.content_type or "image/png",
                        )
                        # mammoth defaults the <img alt="..."> to the docx's
                        # stored altText. For images pasted from QQ/Tencent
                        # etc., that altText is the original local file path
                        # ("C:\\Documents and Settings\\...\\foo.jpg") which
                        # leaks into the markdown as ![<junk path>](src).
                        # Strip alt when it looks like a filesystem path.
                        raw_alt = getattr(image, "alt_text", "") or ""
                        if _looks_like_local_path(raw_alt):
                            raw_alt = ""
                        return {"src": filename, "alt": raw_alt}
                    except Exception:
                        return {"src": ""}

                mammoth_options["convert_image"] = mammoth.images.img_element(
                    save_image_to_disk
                )
        elif kwargs.get("keep_data_uris", False):
            mammoth_options["convert_image"] = mammoth.images.data_uri

        return self._html_converter.convert_string(
            mammoth.convert_to_html(pre_process_stream, **mammoth_options).value,
            **kwargs,
        )
