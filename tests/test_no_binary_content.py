# SPDX-License-Identifier: AGPL-3.0-only
"""Guard: no copyrighted/binary content may ever be committed. See CONTENT_POLICY.md."""

from __future__ import annotations

import subprocess
from pathlib import Path

FORBIDDEN_EXT = {
    ".psarc",
    ".sng",
    ".ogg",
    ".oga",
    ".mp3",
    ".wav",
    ".flac",
    ".m4a",
    ".opus",
    ".wem",
    ".bnk",
    ".pck",
    ".dds",
    ".hsan",
    ".hson",
    ".feedpak",
    ".sloppak",
}


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    )
    return out.stdout.split()


def test_no_forbidden_extensions() -> None:
    bad = [f for f in _tracked_files() if Path(f).suffix.lower() in FORBIDDEN_EXT]
    assert not bad, f"Forbidden content committed (see CONTENT_POLICY.md): {bad}"
