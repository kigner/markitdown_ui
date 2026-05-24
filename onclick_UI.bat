@echo off
REM Launch MarkItDown GUI using the project's venv.
REM Place this file in the repo root.

setlocal

set "VENV_PY=%~dp0venv\Scripts\pythonw.exe"
set "VENV_PY_CONSOLE=%~dp0venv\Scripts\python.exe"

if not exist "%VENV_PY_CONSOLE%" (
    echo [ERROR] venv not found at %~dp0venv
    echo Create it first:
    echo     python -m venv venv
    echo     venv\Scripts\python -m pip install -e packages\markitdown[all]
    echo     venv\Scripts\python -m pip install -e packages\markitdown-gui
    pause
    exit /b 1
)

REM Use pythonw.exe (no console window) when available; fall back to python.exe.
if exist "%VENV_PY%" (
    start "" "%VENV_PY%" -m markitdown_gui
) else (
    "%VENV_PY_CONSOLE%" -m markitdown_gui
)

endlocal
