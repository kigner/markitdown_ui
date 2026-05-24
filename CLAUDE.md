# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MarkItDown** is a Python utility for converting various file formats to Markdown, designed primarily for use with LLMs and text analysis pipelines. Built by Microsoft's AutoGen team.

- Python 3.10+
- MIT License
- PyPI: `pip install 'markitdown[all]'`

## Monorepo Structure

The repo contains multiple packages under `packages/`:

| Package | Purpose |
|---------|---------|
| `markitdown/` | Core library — main converter engine |
| `markitdown-ocr/` | OCR plugin (LLM Vision for embedded images) |
| `markitdown-mcp/` | MCP server for MarkItDown |
| `markitdown-sample-plugin/` | Sample plugin for 3rd-party development |

All work below focuses on the core `packages/markitdown/` package.

## Core Architecture

### Converter Registry Pattern

The `MarkItDown` class (`src/markitdown/_markitdown.py`) maintains a registry of `DocumentConverter` instances sorted by priority:

1. Opens a file stream
2. Uses **Magika** to identify file type
3. Iterates through converters in priority order
4. Each converter's `accepts()` method determines if it can handle the file
5. First converter that succeeds returns a `DocumentConverterResult`

### Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `MarkItDown` | `_markitdown.py` | Main entry point. Methods: `convert()`, `convert_local()`, `convert_stream()`, `convert_uri()`, `convert_response()` |
| `DocumentConverter` | `_base_converter.py` | Abstract base class with `accepts()` and `convert()` methods |
| `DocumentConverterResult` | `_base_converter.py` | Contains `markdown` and `title` fields |
| `StreamInfo` | `_stream_info.py` | Frozen dataclass: mimetype, extension, charset, filename, local_path, url |

### Priority System

- `PRIORITY_SPECIFIC_FILE_FORMAT = 0.0` — Specific converters (docx, pdf, xlsx, etc.)
- `PRIORITY_GENERIC_FILE_FORMAT = 10.0` — Generic converters (plain text, HTML, ZIP)

Lower values are tried first. When adding a new format-specific converter, use `0.0`.

### Plugin System

Plugins are discovered via entry points (`markitdown.plugin`). Entry points are defined in `pyproject.toml`:

```toml
[project.entry-points."markitdown.plugin"]
ocr = "markitdown_ocr"
sample_plugin = "markitdown_sample_plugin"
```

### Directory Layout (core package)

```
packages/markitdown/
  src/markitdown/
    __init__.py          # Public exports: MarkItDown, DocumentConverter, StreamInfo, exceptions
    __main__.py          # CLI entry point (argparse)
    _markitdown.py       # Core class, converter registration, dispatch logic
    _base_converter.py   # DocumentConverter base class + DocumentConverterResult
    _stream_info.py      # StreamInfo dataclass
    _exceptions.py       # Exception types
    _uri_utils.py        # URI parsing helpers
    converters/          # Format-specific converters
    converter_utils/     # Shared utilities (e.g., docx/math helpers)
  tests/
    _test_vectors.py     # Test data definitions (FileTestVector)
    test_module_vectors.py   # Main conversion tests
    test_cli_*.py            # CLI tests
    test_pdf_*.py            # PDF-specific tests
    test_files/              # Test fixture files
```

## Development Commands

### Setup

```bash
pip install hatch
hatch shell
pip install -e 'packages/markitdown[all]'
```

### Running Tests

```bash
cd packages/markitdown
hatch test
# Or with pytest directly:
cd packages/markitdown
pytest
# Run a specific test:
pytest tests/test_module_vectors.py -k "pdf"
```

The test environment includes all optional features plus `openai` (see `pyproject.toml` `[tool.hatch.envs.hatch-test]`).

### Type Checking

```bash
hatch run types:check
# Runs: mypy --install-types --non-interactive --ignore-missing-imports src/markitdown tests
```

### Pre-commit / Linting

```bash
pre-commit run --all-files
```

Only uses **Black** formatter (configured in `.pre-commit-config.yaml`).

### Docker

```bash
docker build -t markitdown:latest .
docker run --rm -i markitdown:latest < ~/your-file.pdf > output.md
```

## Adding a New Converter

1. Create a new file in `src/markitdown/converters/` named `_yourformat_converter.py`
2. Inherit from `DocumentConverter` and implement `accepts()` and `convert()`
3. Set `_priority = PRIORITY_SPECIFIC_FILE_FORMAT` (0.0) for format-specific converters
4. Export from `converters/__init__.py`
5. Register in `MarkItDown.__init__()` via `_register_converter()`
6. Add test fixtures to `tests/test_files/` and vectors to `tests/_test_vectors.py`
7. If the converter needs an optional dependency, add an extra in `pyproject.toml` `[project.optional-dependencies]`

## Optional Dependencies

Installed via extras: `[pptx]`, `[docx]`, `[xlsx]`, `[xls]`, `[pdf]`, `[outlook]`, `[audio-transcription]`, `[youtube-transcription]`, `[az-doc-intel]`, `[az-content-understanding]`, `[all]`

When a converter requires an optional dependency, import it inside the converter class and raise `MissingDependencyException` if unavailable.
