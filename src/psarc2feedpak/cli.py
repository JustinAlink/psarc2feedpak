# SPDX-License-Identifier: AGPL-3.0-only
"""Command-line entry point for psarc2feedpak.

Posture (see LEGAL.md / CONTENT_POLICY.md): this tool CONVERTS an already-
unpacked arrangement into the open ``.feedpak`` format. It does NOT decrypt or
circumvent any access control. If handed a still-packed ``.psarc`` it explains
how to unpack it yourself — it will never fetch or run a decryptor.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

__all__ = ["main"]

# PSARC container magic (big-endian 'PSAR'). A file starting with this is a
# packed archive; our input is the *unpacked* project, so we guide instead.
_PSARC_MAGIC = b"PSAR"

# General-purpose tools a user may already have installed to unpack a .psarc
# they own. We only *detect and name* these — we never fetch or run them.
_KNOWN_UNPACKERS = ("RocksmithToolkitCLI", "psarc", "psarc.py", "unpsarc")


def _looks_packed(path: Path) -> bool:
    """True if ``path`` is a raw, still-packed PSARC container (magic 'PSAR')."""
    try:
        with path.open("rb") as fh:
            return fh.read(4) == _PSARC_MAGIC
    except OSError:
        return False


def _detect_unpacker() -> str | None:
    for name in _KNOWN_UNPACKERS:
        found = shutil.which(name)
        if found:
            return found
    return None


def _guide_unpack(path: Path) -> int:
    """Explain how to unpack a still-packed ``.psarc``. We never do this step."""
    print(
        f"'{path.name}' is a still-packed PSARC container.\n"
        "psarc2feedpak converts already-unpacked arrangements; it does not "
        "unpack\nor decrypt protected content.\n",
        file=sys.stderr,
    )
    tool = _detect_unpacker()
    if tool:
        print(
            f"Detected an unpacker on your PATH: {tool}\n"
            "Unpack your own file with it, then re-run me on the output folder:\n"
            "    psarc2feedpak <unpacked-folder> -o out/",
            file=sys.stderr,
        )
    else:
        print(
            "Unpack it first with your own PSARC / Rocksmith toolkit into a\n"
            "project folder, then run:\n"
            "    psarc2feedpak <unpacked-folder> -o out/",
            file=sys.stderr,
        )
    return 2


def _convert(input_dir: Path, out_dir: Path, *, legacy_ext: bool, dry_run: bool) -> int:
    """Convert one unpacked arrangement, or every project under a parent folder."""
    from psarc2feedpak.audio.normalize import WemConversionError
    from psarc2feedpak.convert.pipeline import ConversionError, convert_any

    def _progress(i: int, total: int, name: str) -> None:
        print(f"  [{i + 1}/{total}] {name}")

    try:
        summary = convert_any(
            input_dir,
            out_dir,
            legacy_ext=legacy_ext,
            dry_run=dry_run,
            on_progress=None if dry_run else _progress,
        )
    except (ConversionError, WemConversionError) as exc:
        print(f"psarc2feedpak: {exc}", file=sys.stderr)
        return 1

    converted, failed = summary["converted"], summary["failed"]

    if dry_run:
        for r in converted:
            print(f"[dry-run] {r['title']!r} ({r['duration']}s) -> {r['would_write']}")
        return 0

    if summary["mode"] == "single":
        r = converted[0]
        print(f"wrote {r['pak']}")
        print(
            f"  {r['title']!r} — {r['artist']!r}  ({r['duration']}s)  "
            f"arrangements: {', '.join(a['id'] for a in r['arrangements'])}  "
            f"cover: {'yes' if r['cover'] else 'no'}"
        )
        return 0

    tail = f", {len(failed)} failed:" if failed else ""
    print(f"\nBatch: {len(converted)}/{summary['total']} converted{tail}")
    for f in failed:
        print(f"  ✗ {f['name']}: {f['error']}", file=sys.stderr)
    return 1 if failed and not converted else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="psarc2feedpak",
        description=(
            "Convert an UNPACKED arrangement — or a whole folder of them — you own "
            "into the open .feedpak format."
        ),
    )
    parser.add_argument(
        "input",
        type=Path,
        help="an unpacked arrangement folder, OR a parent folder of them (batch); "
        "a raw .psarc is explained, not decrypted",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("out"),
        help="output directory (default: ./out)",
    )
    parser.add_argument(
        "--legacy-ext",
        action="store_true",
        help="write the legacy .sloppak extension instead of .feedpak",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="inspect without writing output",
    )
    args = parser.parse_args(argv)

    src: Path = args.input
    if not src.exists():
        print(f"input not found: {src}", file=sys.stderr)
        return 2

    if src.is_file():
        if _looks_packed(src):
            return _guide_unpack(src)
        print(
            f"'{src.name}' is a file, not an unpacked arrangement folder.\n"
            "Point me at the folder produced by unpacking your .psarc.",
            file=sys.stderr,
        )
        return 2

    return _convert(src, args.output, legacy_ext=args.legacy_ext, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
