# SPDX-License-Identifier: AGPL-3.0-only
"""Convert an unpacked Rocksmith arrangement folder into a .feedpak.

Reuses the feedBack core's own RS2014 arrangement parser
(``song.parse_arrangement``) and wire encoder (``song.arrangement_to_wire``) —
the exact code feedBack itself uses — so the per-phrase max-difficulty merge and
every technique are handled correctly rather than re-implemented (and re-bugged).
The core is pure XML parsing (no decryption); we locate it via ``$SLOPSMITH_DIR``
or a sibling checkout. This module performs NO decryption: it consumes files an
unpacker (e.g. DLC Builder) already produced from content you own.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from psarc2feedpak.audio.normalize import wem_to_ogg

__all__ = ["convert", "convert_any", "batch_convert", "validate", "ConversionError"]

FEEDPAK_VERSION = "1.2.0"

# DLC-Builder-normalized arrangement files -> (id, fallback display name).
_ARR_FILES = [
    ("arr_lead_RS2.xml", "lead", "Lead"),
    ("arr_rhythm_RS2.xml", "rhythm", "Rhythm"),
    ("arr_bass_RS2.xml", "bass", "Bass"),
]

# Roles we can recognise in an arrangement filename, in pack order.
_ROLES = ("lead", "rhythm", "bass", "combo")

# Ceiling on how many XML files the layout probe will open. It exists to find
# arrangements another unpacker nested, not to trawl an arbitrary tree.
_MAX_XML_PROBE = 200


class ConversionError(RuntimeError):
    pass


# ── feedBack core location + import ──────────────────────────────────────────
def _locate_core() -> Path:
    cands: list[Path] = []
    env = os.environ.get("SLOPSMITH_DIR") or os.environ.get("FEEDBACK_CORE")
    if env:
        cands.append(Path(env))
    # PyInstaller-bundled core (standalone .exe builds ship it as data).
    if getattr(sys, "frozen", False):
        cands.append(Path(getattr(sys, "_MEIPASS", ".")) / "feedback_core")
    here = Path(__file__).resolve()
    cands.append(here.parents[3].parent / "slopsmith")  # sibling of the repo
    cands.append(Path.home() / "Documents" / "Coding Projects" / "slopsmith")
    for c in cands:
        if c and (c / "lib" / "song.py").exists():
            return c
    raise ConversionError(
        "feedBack core not found. Set $SLOPSMITH_DIR to a got-feedback/feedback checkout."
    )


def _import_song():
    """Import just the core's ``song`` module (stdlib-only) — all the convert
    path needs. Kept separate from ``sloppak`` so a bundled .exe stays lean and
    doesn't drag in sloppak's heavier transitive deps."""
    core = _locate_core()
    for p in (str(core), str(core / "lib")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import song  # type: ignore

    _patch_lefthand(song)
    return song


def _import_core():
    """``song`` + ``sloppak`` — the latter only used by :func:`validate`."""
    song = _import_song()
    import sloppak  # type: ignore

    return song, sloppak


def _patch_lefthand(song) -> None:
    """RS2014 stores the fret-hand finger in ``leftHand``; the core's
    ``_parse_note`` reads only ``fretFinger`` (the GP-import spelling), silently
    dropping all fingering. Patch it to fall back to ``leftHand`` (a §6.2.2
    teaching mark). Idempotent; never feeds a grader."""
    if getattr(song, "_p2f_lefthand_patched", False):
        return
    orig = song._parse_note

    def patched(n):
        note = orig(n)
        if note.fret_finger == -1:
            lh = n.get("leftHand")
            if lh is not None:
                try:
                    note.fret_finger = int(lh)
                except (TypeError, ValueError):
                    pass
        return note

    song._parse_note = patched
    song._p2f_lefthand_patched = True


# ── XML helpers ──────────────────────────────────────────────────────────────
def _text(root, tag: str, default: str = "") -> str:
    el = root.find(tag)
    return el.text.strip() if el is not None and el.text else default


def _extract_metadata(arr_xml: Path) -> dict:
    root = ET.parse(str(arr_xml)).getroot()

    def num(tag, cast, default):
        try:
            return cast(_text(root, tag, "") or default)
        except (TypeError, ValueError):
            return cast(default)

    return {
        "title": _text(root, "title"),
        "artist": _text(root, "artistName"),
        "album": _text(root, "albumName"),
        "duration": round(num("songLength", float, 0.0), 3),
        "year": num("albumYear", int, 0),
    }


def _parse_beats(root) -> list:
    out = []
    for eb in root.findall(".//ebeat"):
        t = eb.get("time")
        if t is None:
            continue
        out.append(
            {"time": round(float(t), 3), "measure": int(eb.get("measure", "-1"))}
        )
    return out


def _parse_sections(root) -> list:
    out = []
    for i, sec in enumerate(root.findall(".//section"), 1):
        out.append(
            {
                "name": sec.get("name", ""),
                "number": int(sec.get("number", str(i))),
                "time": round(float(sec.get("startTime", "0") or 0), 3),
            }
        )
    return out


def _find_full_wem(project: Path) -> Path | None:
    wems = [p for p in project.rglob("*.wem") if "preview" not in p.name.lower()]
    return max(wems, key=lambda p: p.stat().st_size) if wems else None


def _find_cover_dds(project: Path) -> Path | None:
    for pat in (
        "gfxassets/album_art/*_256.dds",
        "*_256.dds",
        "**/*_256.dds",
        "*.dds",
        "**/*.dds",
    ):
        hits = sorted(project.glob(pat))
        if hits:
            return hits[0]
    return None


def _build_zip(src_dir: Path, zip_path: Path) -> None:
    """Deterministic, POSIX-path zip (matches the core's benchmark builder)."""
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                info = zipfile.ZipInfo(
                    filename=p.relative_to(src_dir).as_posix(),
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o644 & 0xFFFF) << 16
                info.create_system = 3
                zf.writestr(info, p.read_bytes())


def _root_tag(path: Path) -> str | None:
    """The document's root tag, without parsing the whole file. Charts run to
    megabytes and classifying one only needs its first start event."""
    try:
        for _event, elem in ET.iterparse(str(path), events=("start",)):
            return str(elem.tag)
    except (ET.ParseError, OSError):
        return None
    return None


def _role_of(stem: str) -> str | None:
    """Map a filename stem onto a known arrangement role, so the Toolkit's
    ``bromptoncocktail_bass`` yields ``bass`` rather than a per-song id."""
    s = stem.lower()
    for role in _ROLES:
        if re.search(rf"(?:^|[_\-\s]){role}\d*(?:[_\-\s]|$)", s):
            return role
    return None


def _discover_arrangements(project: Path) -> list[tuple[str, str, str]]:
    """Find the instrumental arrangements in an unpacked project.

    Returns ``(path_relative_to_project, id, display_name)``. The path is
    relative rather than a bare filename because unpackers disagree on layout:
    DLC Builder drops ``arr_lead_RS2.xml`` beside the audio, while the
    Rocksmith Toolkit nests ``songs/arr/<song>_lead.xml``. Returning just the
    name silently broke every nested layout: the caller resolved it against
    the project root and died on FileNotFoundError.
    """
    present = [(fn, aid, nm) for (fn, aid, nm) in _ARR_FILES if (project / fn).exists()]
    if present:
        return present

    # Any other unpacker: take XML whose root element is <song>, nearest
    # first. That check is also what filters out the vocals (<vocals>) and
    # showlights (<showlights>) files sitting in the same folder.
    seen: set[Path] = set()
    cands: list[Path] = []
    for pattern in ("*.xml", "songs/arr/*.xml", "**/*.xml"):
        for cand in sorted(project.glob(pattern)):
            resolved = cand.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            cands.append(cand)
            if len(cands) >= _MAX_XML_PROBE:
                break
        if len(cands) >= _MAX_XML_PROBE:
            break

    used: set[str] = set()
    for cand in cands:
        if _root_tag(cand) != "song":
            continue
        aid = _role_of(cand.stem) or cand.stem.lower().replace("arr_", "").replace(
            "_rs2", ""
        )
        aid = aid or cand.stem.lower()
        base, n = aid, 2
        while aid in used:  # two files claiming one role must both survive
            aid, n = f"{base}{n}", n + 1
        used.add(aid)
        present.append(
            (cand.relative_to(project).as_posix(), aid, aid.replace("_", " ").title())
        )

    # Lead first: convert() hangs the song-level beats and sections off
    # whichever arrangement lands at index 0.
    order = {role: i for i, role in enumerate(_ROLES)}
    present.sort(
        key=lambda a: (order.get(a[1].rstrip("0123456789"), len(_ROLES)), a[1])
    )
    return present


# ── pipeline ─────────────────────────────────────────────────────────────────
def convert(
    project_dir, out_dir, *, legacy_ext: bool = False, dry_run: bool = False
) -> dict:
    song = _import_song()
    project = Path(project_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    present = _discover_arrangements(project)
    if not present:
        raise ConversionError(f"no RS2014 arrangement XML found under {project}")

    meta = _extract_metadata(project / present[0][0])
    stem = (meta["title"] or project.name).replace("/", "-").strip() or "song"
    ext = ".sloppak" if legacy_ext else ".feedpak"

    if dry_run:
        return {
            "title": meta["title"],
            "arrangements": [p[1] for p in present],
            "duration": meta["duration"],
            "would_write": str(out_dir / (stem + ext)),
        }

    stage = out_dir / f".{stem}.stage"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "arrangements").mkdir(parents=True)
    (stage / "stems").mkdir()

    manifest_arrs = []
    for idx, (fn, aid, name) in enumerate(present):
        xml_path = project / fn
        arr = song.parse_arrangement(str(xml_path))
        wire = song.arrangement_to_wire(arr)
        # Beats/sections are song-level in the RS XML but the loader reads them
        # from the (first) arrangement JSON — attach them to the primary arr.
        if idx == 0:
            root = ET.parse(str(xml_path)).getroot()
            wire["beats"] = _parse_beats(root)
            wire["sections"] = _parse_sections(root)
        (stage / "arrangements" / f"{aid}.json").write_text(
            json.dumps(wire, separators=(",", ":")), encoding="utf-8"
        )
        manifest_arrs.append(
            {
                "id": aid,
                "name": getattr(arr, "name", None) or name,
                "file": f"arrangements/{aid}.json",
                "tuning": list(arr.tuning),
                "capo": int(getattr(arr, "capo", 0) or 0),
            }
        )

    full_wem = _find_full_wem(project)
    if full_wem is None:
        raise ConversionError("no full-mix .wem found in project")
    wem_to_ogg(full_wem, stage / "stems" / "full.ogg")

    cover_key = None
    dds = _find_cover_dds(project)
    if dds is not None:
        cover_out = stage / "cover.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(dds), str(cover_out)],
            capture_output=True,
            text=True,
        )
        if cover_out.exists() and cover_out.stat().st_size > 0:
            cover_key = "cover.jpg"

    manifest = {
        "feedpak_version": FEEDPAK_VERSION,
        "title": meta["title"],
        "artist": meta["artist"],
        "album": meta["album"],
        "year": meta["year"],
        "duration": meta["duration"],
        "arrangements": manifest_arrs,
        "stems": [{"id": "full", "file": "stems/full.ogg", "default": True}],
    }
    if cover_key:
        manifest["cover"] = cover_key

    import yaml  # provided by the core's runtime deps

    (stage / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    pak = out_dir / (stem + ext)
    _build_zip(stage, pak)
    shutil.rmtree(stage)

    return {
        "pak": pak,
        "title": meta["title"],
        "artist": meta["artist"],
        "duration": meta["duration"],
        "arrangements": manifest_arrs,
        "cover": bool(cover_key),
    }


def validate(pak: Path) -> dict:
    """Acceptance-test the produced pack via the core's own loader."""
    import tempfile

    _song, sloppak = _import_core()
    pak = Path(pak)
    meta = sloppak.extract_meta(pak)
    with tempfile.TemporaryDirectory() as cache:
        loaded = sloppak.load_song(pak.name, pak.parent, Path(cache))
    return {"meta": meta, "loaded": loaded}


# ── batch ────────────────────────────────────────────────────────────────────
def _find_projects(parent: Path) -> list[Path]:
    """Immediate subfolders of ``parent`` that are unpacked arrangement projects."""
    if not parent.is_dir():
        return []
    return [
        d for d in sorted(parent.iterdir()) if d.is_dir() and _discover_arrangements(d)
    ]


def batch_convert(
    projects,
    out_dir,
    *,
    legacy_ext: bool = False,
    dry_run: bool = False,
    on_progress=None,
) -> dict:
    """Convert a list of unpacked project folders. Never aborts on one bad song —
    failures are collected and returned. ``on_progress(index, total, name)`` is
    called before each conversion."""
    projects = [Path(p) for p in projects]
    total = len(projects)
    converted: list[dict] = []
    failed: list[dict] = []
    for i, proj in enumerate(projects):
        if on_progress is not None:
            on_progress(i, total, proj.name)
        try:
            converted.append(
                convert(proj, out_dir, legacy_ext=legacy_ext, dry_run=dry_run)
            )
        except Exception as exc:  # one bad song must not sink the whole batch
            failed.append({"dir": str(proj), "name": proj.name, "error": str(exc)})
    return {"mode": "batch", "total": total, "converted": converted, "failed": failed}


def convert_any(
    input_dir,
    out_dir,
    *,
    legacy_ext: bool = False,
    dry_run: bool = False,
    on_progress=None,
) -> dict:
    """Convert one unpacked project, or every project under a parent folder.

    Auto-detects: if ``input_dir`` is itself an unpacked arrangement it is
    converted on its own; otherwise its immediate project subfolders are all
    converted (batch). Returns a summary with ``mode``/``total``/``converted``/``failed``.
    """
    p = Path(input_dir)
    if _discover_arrangements(p):
        result = convert(p, out_dir, legacy_ext=legacy_ext, dry_run=dry_run)
        return {"mode": "single", "total": 1, "converted": [result], "failed": []}
    projects = _find_projects(p)
    if not projects:
        raise ConversionError(
            f"no unpacked arrangements found in {p} (neither here nor in its subfolders)"
        )
    return batch_convert(
        projects,
        out_dir,
        legacy_ext=legacy_ext,
        dry_run=dry_run,
        on_progress=on_progress,
    )
