# SPDX-License-Identifier: AGPL-3.0-only
"""PyInstaller entry point for the CLI exe."""
import sys

from psarc2feedpak.cli import main

if __name__ == "__main__":
    sys.exit(main())
