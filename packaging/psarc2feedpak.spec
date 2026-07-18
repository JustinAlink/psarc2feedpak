# SPDX-License-Identifier: AGPL-3.0-only
# PyInstaller spec — builds psarc2feedpak(.exe) [CLI] and psarc2feedpak-gui(.exe)
# [GUI] as self-contained binaries. The feedBack core's stdlib-only `song`
# parser is bundled as data under feedback_core/, which pipeline._locate_core
# resolves via sys._MEIPASS when frozen.
#
# Requires $SLOPSMITH_DIR to point at a got-feedback/feedback checkout.
# Cross-platform: the datas list avoids the OS-specific --add-data separator.
import os
from pathlib import Path

_pkg = Path(SPECPATH)  # noqa: F821  (PyInstaller injects SPECPATH)
_repo = _pkg.parent
_src = _repo / "src"
_core = Path(os.environ["SLOPSMITH_DIR"]).resolve()

if not (_core / "lib" / "song.py").exists():
    raise SystemExit(f"SLOPSMITH_DIR={_core} is not a feedBack core (no lib/song.py)")

_datas = [(str(_core / "lib"), os.path.join("feedback_core", "lib"))]
_hidden = ["yaml"]


def _exe(entry, name, console):
    analysis = Analysis(  # noqa: F821
        [str(_pkg / entry)],
        pathex=[str(_src)],
        datas=_datas,
        hiddenimports=_hidden,
    )
    pyz = PYZ(analysis.pure)  # noqa: F821
    return EXE(  # noqa: F821
        pyz,
        analysis.scripts,
        analysis.binaries,
        analysis.datas,
        [],
        name=name,
        console=console,
        upx=False,
        strip=False,
    )


cli = _exe("cli_launcher.py", "psarc2feedpak", True)
gui = _exe("gui_launcher.py", "psarc2feedpak-gui", False)
