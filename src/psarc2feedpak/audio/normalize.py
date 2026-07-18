# SPDX-License-Identifier: AGPL-3.0-only
"""Convert Wwise .wem audio to Ogg Vorbis for stems/full.ogg.

This is plain audio *format* conversion (Wwise-Vorbis -> Ogg-Vorbis) — .wem is
NOT encrypted, so this is not a decryption step. Uses ww2ogg + revorb, discovered
from $WW2OGG/$REVORB, the PATH, or a local DLC Builder install.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

__all__ = ["wem_to_ogg", "WemConversionError"]

# DLC Builder bundles ww2ogg + revorb + the aoTuV codebook here on Linux.
_DLC_TOOLS = Path.home() / "tools" / "DLCBuilder" / "dlcbuilder-linux" / "Tools"


class WemConversionError(RuntimeError):
    pass


def _find(name: str, env: str) -> Path | None:
    v = os.environ.get(env)
    if v and Path(v).exists():
        return Path(v)
    which = shutil.which(name)
    if which:
        return Path(which)
    cand = _DLC_TOOLS / name
    return cand if cand.exists() else None


def _find_codebook(ww2ogg: Path) -> Path | None:
    for base in (ww2ogg.parent, _DLC_TOOLS):
        for name in ("packed_codebooks_aoTuV_603.bin", "packed_codebooks.bin"):
            c = base / name
            if c.exists():
                return c
    return None


def wem_to_ogg(wem: Path, out_ogg: Path) -> Path:
    """Convert a .wem to an Ogg Vorbis file at out_ogg. Raises on failure."""
    ww2ogg = _find("ww2ogg", "WW2OGG")
    if ww2ogg is None:
        raise WemConversionError(
            "ww2ogg not found. Install DLC Builder (bundles it) or set $WW2OGG."
        )
    out_ogg.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(ww2ogg), str(wem), "-o", str(out_ogg)]
    codebook = _find_codebook(ww2ogg)
    if codebook is not None:
        cmd += ["--pcb", str(codebook)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out_ogg.exists() or out_ogg.stat().st_size == 0:
        raise WemConversionError(f"ww2ogg failed:\n{proc.stderr or proc.stdout}")
    # revorb fixes the Ogg granule positions ww2ogg leaves behind.
    revorb = _find("revorb", "REVORB")
    if revorb is not None:
        subprocess.run([str(revorb), str(out_ogg)], capture_output=True, text=True)
    return out_ogg
