# MarkItDown GUI

Desktop GUI wrapper around [MarkItDown](https://github.com/microsoft/markitdown) for batch
converting Word / PDF / PowerPoint / Excel / image / HTML / etc. files to Markdown.

## Install

```bash
pip install -e packages/markitdown-gui
```

(Installs `markitdown[all]` and `PySide6`. On Windows it also installs `pywin32` so that
legacy `.doc` files can be auto-converted via Microsoft Word.)

## Portable package (Windows, no install required)

Pre-built integrated package: bundled Python 3.12 runtime with all dependencies. Extract
and double-click `onclick_UI.exe` — no Python install, no virtual environment, no
`pip install` step needed.

If the GUI fails to open, double-click `onclick_UI_debug.bat` to run the same launch in
a visible console so the traceback can be read.

- Google Drive: <https://drive.google.com/drive/folders/1qEXSxqU44FhShZ2FeorBypxsO9-DUIEg>
- Baidu Drive: <https://pan.baidu.com/s/1RHSeEBj2KDscC_XYCU9auA?pwd=gacr> (code: `gacr`)

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
