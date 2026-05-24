#!/bin/bash
# Launch MarkItDown GUI using the project's venv (macOS).
# Place this file in the repo root. Double-click in Finder to run.
# First time: `chmod +x MacOS_onclick.command` to make it executable.

# cd to the script's own directory so relative paths work when double-clicked
cd "$(dirname "$0")" || exit 1

VENV_PY="venv/bin/python"
VENV_PYW="venv/bin/pythonw"

if [ ! -x "$VENV_PY" ]; then
    echo "[ERROR] venv not found at $(pwd)/venv"
    echo "Create it first:"
    echo "    python3 -m venv venv"
    echo "    venv/bin/python -m pip install -e packages/markitdown[all]"
    echo "    venv/bin/python -m pip install -e packages/markitdown-gui"
    echo
    read -r -p "Press Enter to close..." _
    exit 1
fi

# Prefer pythonw (GUI-mode, no Terminal window) if the python.org installer
# provided one; otherwise fall back to python.
if [ -x "$VENV_PYW" ]; then
    "$VENV_PYW" -m markitdown_gui &
    disown
else
    "$VENV_PY" -m markitdown_gui
fi
