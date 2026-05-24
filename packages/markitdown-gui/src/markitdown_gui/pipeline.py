"""Input scanning and output-path planning for the GUI batch pipeline."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


SUPPORTED_EXTS = {
    ".docx", ".doc",  # .doc handled via Word COM pre-conversion
    ".pdf",
    ".pptx", ".ppt",  # .ppt handled via PowerPoint COM pre-conversion
    ".xlsx", ".xls",
    ".csv",
    ".html", ".htm",
    ".txt", ".md",
    ".ipynb",
    ".msg",
    ".epub",
    ".zip",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp",
    ".mp3", ".wav", ".m4a", ".flac",
}


class ImageMode(str, Enum):
    EXTRACT = "extract"
    EMBED = "embed"
    IGNORE = "ignore"


class InputMode(str, Enum):
    BATCH = "batch"            # one folder, recurse
    SINGLE_OR_MULTI = "files"  # one or more files


@dataclass
class FileJob:
    """One file to convert."""

    src_path: str             # original file on disk
    md_path: str              # absolute output .md path
    md_basename: str          # stem of md_path (used as image-name prefix)
    images_dir: str           # absolute shared images dir
    is_legacy_doc: bool       # .doc that needs Word pre-conversion
    is_legacy_ppt: bool       # .ppt that needs PowerPoint pre-conversion


@dataclass
class Plan:
    output_root: str          # the consolidated output dir (e.g. <out>/<input>_markdown)
    images_dir: str           # output_root + "/images"
    jobs: List[FileJob]
    skipped_unsupported: List[str]
    legacy_doc_count: int     # how many of `jobs` are .doc
    legacy_ppt_count: int     # how many of `jobs` are .ppt


_SAFE_NAME_RE = re.compile(r"[^\w\-_. ]")


def _sanitize_segment(seg: str) -> str:
    seg = _SAFE_NAME_RE.sub("_", seg).strip()
    return seg or "_"


def _is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTS


def _gather_files(
    inputs: Sequence[str], mode: InputMode
) -> tuple[list[Path], Optional[Path]]:
    """Return (list of files, input root for relative-path prefixing).

    In BATCH mode the single input is a directory; root is that dir.
    In file mode the root is None (no prefixing needed).
    """
    if mode == InputMode.BATCH:
        if len(inputs) != 1:
            raise ValueError("batch mode expects exactly one directory")
        root = Path(inputs[0])
        if not root.is_dir():
            raise ValueError(f"not a directory: {root}")
        files = sorted(p for p in root.rglob("*") if p.is_file())
        return files, root
    else:
        files = [Path(p) for p in inputs]
        return files, None


def _make_md_name(src: Path, root: Optional[Path]) -> str:
    """Compute the .md filename. For nested files, prepend ancestor dir names.

    foo/file.docx                 -> file.md
    foo/sub/file.docx (root=foo)  -> sub_file.md
    foo/a/b/file.docx (root=foo)  -> a_b_file.md
    Multi-file mode (root=None)   -> file.md (with index suffix on collision)
    """
    stem = _sanitize_segment(src.stem)
    if root is None:
        return f"{stem}.md"
    try:
        rel = src.relative_to(root)
    except ValueError:
        return f"{stem}.md"
    parts = [_sanitize_segment(p) for p in rel.parts[:-1]]
    if parts:
        return "_".join(parts + [stem]) + ".md"
    return f"{stem}.md"


def plan(
    inputs: Sequence[str],
    mode: InputMode,
    output_dir: str,
) -> Plan:
    """Scan inputs and build a Plan with one FileJob per supported file."""
    files, root = _gather_files(inputs, mode)

    # Choose the consolidated output folder.
    # Batch mode: <out>/<input_dirname>_markdown/
    # Single / multi-file mode: <out>/markdown/
    if mode == InputMode.BATCH and root is not None:
        output_root = os.path.join(output_dir, f"{root.name}_markdown")
    else:
        output_root = os.path.join(output_dir, "markdown")

    images_dir = os.path.join(output_root, "images")

    jobs: list[FileJob] = []
    skipped: list[str] = []
    legacy_doc_count = 0
    legacy_ppt_count = 0
    used_md_names: set[str] = set()

    for f in files:
        if not _is_supported(f):
            skipped.append(str(f))
            continue
        md_name = _make_md_name(f, root)
        # Avoid collisions in file mode (root=None).
        base, ext = os.path.splitext(md_name)
        candidate = md_name
        idx = 1
        while candidate.lower() in used_md_names:
            candidate = f"{base}_{idx}{ext}"
            idx += 1
        used_md_names.add(candidate.lower())

        md_path = os.path.join(output_root, candidate)
        md_basename = os.path.splitext(candidate)[0]
        suffix = f.suffix.lower()
        is_doc = suffix == ".doc"
        is_ppt = suffix == ".ppt"
        if is_doc:
            legacy_doc_count += 1
        if is_ppt:
            legacy_ppt_count += 1
        jobs.append(
            FileJob(
                src_path=str(f),
                md_path=md_path,
                md_basename=md_basename,
                images_dir=images_dir,
                is_legacy_doc=is_doc,
                is_legacy_ppt=is_ppt,
            )
        )

    return Plan(
        output_root=output_root,
        images_dir=images_dir,
        jobs=jobs,
        skipped_unsupported=skipped,
        legacy_doc_count=legacy_doc_count,
        legacy_ppt_count=legacy_ppt_count,
    )


def build_cli_command(
    job: FileJob,
    image_mode: ImageMode,
    src_override: Optional[str] = None,
) -> list[str]:
    """Build the argv to run `python -m markitdown` for one job.

    `src_override` lets the caller substitute a temporary .docx path (from
    Word-COM pre-conversion of a legacy .doc).
    """
    src = src_override if src_override is not None else job.src_path
    argv = [sys.executable, "-m", "markitdown", "-o", job.md_path]

    if image_mode == ImageMode.EXTRACT:
        argv += [
            "--extract-images",
            "--images-dir", job.images_dir,
            "--image-name-prefix", job.md_basename,
        ]
    elif image_mode == ImageMode.EMBED:
        argv.append("--keep-data-uris")
    # IGNORE: pass nothing — workers.py strips image refs after the subprocess.

    argv.append(src)
    return argv
