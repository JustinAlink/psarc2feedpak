# psarc2feedpak

Convert PSARC archives **you legally own** into the open, hand-editable
`.feedpak` format, so you can play your own content in open-source tools like
feedBack.

> **This tool ships no copyrighted content, and it does not decrypt or
> circumvent anything.** It is a format converter that operates on files
> already unpacked on your machine.

## What it does

- Reads an **unpacked** arrangement (a project folder) that you produced from
  content you own.
- Maps the note-chart + metadata into a neutral intermediate form.
- Writes a `.feedpak` package (open format; `.sloppak` is the legacy alias).

## What it does NOT do

- It does **not** decrypt or unpack `.psarc` files, and it does **not** bypass
  access controls. If you hand it a still-packed `.psarc`, it tells you how to
  unpack it yourself — it will not do that step for you, and it will never
  download or run a decryptor.
- It bundles **no** sample songs, charts, audio, or fixtures.
- It never phones home.

## Pipeline

```
your .psarc ──[your own PSARC / Rocksmith toolkit]──► unpacked project folder
                                                            │
                                                psarc2feedpak (this tool)
                                                            ▼
                                              song.feedpak  →  plays in feedBack
```

Step one (unpacking content you own) uses general-purpose tooling you run
yourself — e.g. the Rocksmith Custom Song Toolkit. **This project is only the
converter.** If you want a one-command experience, chain the two with your own
short wrapper script — that stays on your machine, with your tools.

## Install

    pipx install .            # or, for development:  pip install -e .[dev]

## Usage

    psarc2feedpak <unpacked-folder> -o out/        # writes out/<song>.feedpak
    psarc2feedpak <unpacked-folder> --legacy-ext   # older installs (.sloppak)
    psarc2feedpak song.psarc                        # explains how to unpack first

## Requirements

- **Python 3.10+** and the **feedBack core** on disk (this reuses its proven
  RS2014 parser rather than re-implementing it). Point `$SLOPSMITH_DIR` at a
  [`got-feedback/feedback`](https://github.com/got-feedback/feedback) checkout.
- **ffmpeg** (album-art transcode) and **ww2ogg + revorb** (Wwise `.wem` → Ogg
  Vorbis; both are bundled with DLC Builder, or set `$WW2OGG` / `$REVORB`).

## Status

**Working.** Converts an unpacked arrangement (lead/rhythm/bass) into a
`.feedpak` that loads in feedBack with the full chart intact — notes, chords,
techniques, the per-phrase difficulty merge, beats, sections, fingering, audio,
and cover art — validated by round-tripping through feedBack's own loader with
zero warnings. Vocals, tones, and bend-heavy fidelity are the next items. No
copyrighted bytes are parsed or shipped by this repo.

## Acceptable use

Use only on archives you have a lawful right to convert, for personal
format-shifting / interoperability. You are responsible for your inputs and
outputs. See [LEGAL.md](LEGAL.md) and [CONTENT_POLICY.md](CONTENT_POLICY.md).

## Trademarks

Product and format names are the property of their respective owners. This
project is not affiliated with, endorsed by, or sponsored by any game publisher
or platform holder. Names are used solely to describe input compatibility
(nominative use).

## License

[AGPL-3.0-only](LICENSE).
