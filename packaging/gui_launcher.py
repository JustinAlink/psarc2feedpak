# SPDX-License-Identifier: AGPL-3.0-only
"""PyInstaller entry point for the GUI exe."""
import sys

from psarc2feedpak.gui import main

if __name__ == "__main__":
    sys.exit(main())
