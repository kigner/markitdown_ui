import os
import re
from typing import Optional


_MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/x-emf": ".emf",
    "image/x-wmf": ".wmf",
}


def _content_type_to_extension(content_type: str) -> str:
    content_type = content_type.lower().split(";")[0].strip()
    if content_type in _MIME_TO_EXT:
        return _MIME_TO_EXT[content_type]
    parts = content_type.split("/")
    if len(parts) == 2:
        return "." + parts[1]
    return ".bin"


class ImageExtractor:
    """
    Saves image blobs to a directory on disk with unique filenames.

    Usage:
        extractor = ImageExtractor("/output/images", rel_prefix="images")
        filename = extractor.save_image(blob, content_type="image/png", base_name="chart")
        # -> "images/chart.png"

    If name_prefix is provided, all saved files are prefixed (e.g. "doc1_chart.png").
    """

    def __init__(
        self,
        output_dir: str,
        rel_prefix: str = "",
        name_prefix: str = "",
    ):
        self._output_dir = output_dir
        self._rel_prefix = rel_prefix
        self._name_prefix = re.sub(r"[^\w\-_. ]", "_", name_prefix).strip() if name_prefix else ""
        self._used_names: set[str] = set()
        os.makedirs(output_dir, exist_ok=True)

    def save_image(
        self,
        blob: bytes,
        *,
        content_type: str = "image/png",
        base_name: Optional[str] = None,
    ) -> str:
        extension = _content_type_to_extension(content_type)

        if base_name:
            base_name = re.sub(r"[^\w\-_. ]", "_", base_name).strip()
            if not base_name:
                base_name = "image"
        else:
            base_name = "image"

        if self._name_prefix:
            base_name = f"{self._name_prefix}_{base_name}"

        candidate = base_name + extension
        if candidate not in self._used_names:
            self._used_names.add(candidate)
            filename = candidate
        else:
            counter = 1
            while True:
                candidate = f"{base_name}_{counter}{extension}"
                if candidate not in self._used_names:
                    self._used_names.add(candidate)
                    filename = candidate
                    break
                counter += 1

        full_path = os.path.join(self._output_dir, filename)
        with open(full_path, "wb") as f:
            f.write(blob)

        if self._rel_prefix:
            return os.path.join(self._rel_prefix, filename).replace("\\", "/")
        return filename
