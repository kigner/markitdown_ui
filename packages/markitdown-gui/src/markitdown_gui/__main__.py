"""CLI entry point: `python -m markitdown_gui` or `markitdown-gui`."""

import sys

from .app import run


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
