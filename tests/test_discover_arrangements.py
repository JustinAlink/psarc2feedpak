# SPDX-License-Identifier: AGPL-3.0-only
"""Arrangement discovery across the layouts different unpackers produce.

The invariant under test: every path `_discover_arrangements` returns must
resolve against the project root. A bare filename was returned for nested
layouts, so the Rocksmith Toolkit's `songs/arr/<song>_lead.xml` blew up with
FileNotFoundError the moment the caller tried to read it.
"""

from __future__ import annotations

from pathlib import Path

from psarc2feedpak.convert.pipeline import _discover_arrangements

SONG_XML = "<song><title>T</title><artistName>A</artistName></song>"


def _write(path: Path, body: str = SONG_XML) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _assert_paths_resolve(project: Path, found: list[tuple[str, str, str]]) -> None:
    for rel, _aid, _name in found:
        assert (project / rel).is_file(), f"{rel!r} does not resolve under {project}"


def test_dlc_builder_layout(tmp_path: Path) -> None:
    for role in ("lead", "rhythm", "bass"):
        _write(tmp_path / f"arr_{role}_RS2.xml")

    found = _discover_arrangements(tmp_path)

    assert [a[1] for a in found] == ["lead", "rhythm", "bass"]
    _assert_paths_resolve(tmp_path, found)


def test_toolkit_nested_layout(tmp_path: Path) -> None:
    """The reported crash: arrangements under songs/arr/, no _RS2 suffix."""
    for role in ("lead", "rhythm", "bass"):
        _write(tmp_path / "songs" / "arr" / f"bromptoncocktail_{role}.xml")

    found = _discover_arrangements(tmp_path)

    _assert_paths_resolve(tmp_path, found)
    assert [a[1] for a in found] == ["lead", "rhythm", "bass"]
    assert all(rel.startswith("songs/arr/") for rel, _, _ in found)


def test_vocals_and_showlights_are_not_arrangements(tmp_path: Path) -> None:
    _write(tmp_path / "songs" / "arr" / "song_lead.xml")
    _write(tmp_path / "songs" / "arr" / "song_vocals.xml", "<vocals />")
    _write(tmp_path / "songs" / "arr" / "song_showlights.xml", "<showlights />")

    found = _discover_arrangements(tmp_path)

    assert [a[1] for a in found] == ["lead"]


def test_unknown_nesting_is_still_found(tmp_path: Path) -> None:
    _write(tmp_path / "extracted" / "deep" / "whatever_bass.xml")

    found = _discover_arrangements(tmp_path)

    _assert_paths_resolve(tmp_path, found)
    assert [a[1] for a in found] == ["bass"]


def test_unnamed_roles_stay_distinct(tmp_path: Path) -> None:
    """Two files that map to no known role must not collapse onto one id."""
    _write(tmp_path / "songs" / "arr" / "mystery_one.xml")
    _write(tmp_path / "songs" / "arr" / "mystery_two.xml")

    found = _discover_arrangements(tmp_path)

    assert len(found) == 2
    assert len({a[1] for a in found}) == 2
    _assert_paths_resolve(tmp_path, found)


def test_no_arrangements_returns_empty(tmp_path: Path) -> None:
    _write(tmp_path / "songs" / "arr" / "song_vocals.xml", "<vocals />")
    (tmp_path / "notes.txt").write_text("not xml", encoding="utf-8")

    assert _discover_arrangements(tmp_path) == []
