@echo off
REM Launch MarkItDown GUI using the bundled portable Python runtime.
REM Place this file in the repo root. Extract-and-run — no install needed.

setlocal

set "EMBED_PY=%~dp0python312\pythonw.exe"
set "EMBED_PY_CONSOLE=%~dp0python312\python.exe"

if not exist "%EMBED_PY_CONSOLE%" (
    echo [ERROR] Portable Python runtime not found at %~dp0python312
    echo This launcher expects the bundled python312\ folder shipped with the integrated package.
    echo If you cloned from git, you need to download the integrated package release instead,
    echo or rebuild the runtime by placing a CPython 3.12 embeddable distribution here and running:
    echo     python312\python.exe get-pip.py
    echo     python312\python.exe -m pip install --no-build-isolation hatchling
    echo     python312\python.exe -m pip install --no-build-isolation .\packages\markitdown[all]
    echo     python312\python.exe -m pip install --no-build-isolation .\packages\markitdown-gui
    pause
    exit /b 1
)

REM pythonw.exe runs without a console window; fall back to python.exe if missing.
if exist "%EMBED_PY%" (
    start "" "%EMBED_PY%" -m markitdown_gui
) else (
    "%EMBED_PY_CONSOLE%" -m markitdown_gui
)

endlocal
