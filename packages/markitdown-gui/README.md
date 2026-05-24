# MarkItDown GUI

Desktop GUI wrapper around [MarkItDown](https://github.com/microsoft/markitdown) for batch
converting Word / PDF / PowerPoint / Excel / image / HTML / etc. files to Markdown.

## Install

```bash
pip install -e packages/markitdown-gui
```

(Installs `markitdown[all]` and `PySide6`. On Windows it also installs `pywin32` so that
legacy `.doc` files can be auto-converted via Microsoft Word.)

## Run

```bash
python -m markitdown_gui
# or
markitdown-gui
```

## Features

- **Batch / single / multi-file** input modes
- **Image handling**: extract to `images/` folder, embed as data URI, or ignore
- **Multi-threaded** conversion using `QThreadPool`
- **Multi-language UI**: English + 中文 (extensible via JSON dictionaries)
- **Legacy `.doc` support** on Windows via Word COM automation
- Dark neon and light themes

## Output layout

When converting input directory `D:\docs\foo` to output `D:\out`:

```
D:\out\foo_markdown\
├── file1.md
├── sub1_file2.md      # nested files get directory prefix
└── images\
    ├── file1_image1.png
    └── sub1_file2_chart.png
```
