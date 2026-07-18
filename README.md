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

## Status

**Scaffold (milestone M0).** The container reader, `.sng`/manifest parsers,
intermediate model, and `.feedpak` writer land milestone by milestone. Format
details are validated against a real, user-owned sample before any milestone is
called done. Nothing here parses copyrighted bytes yet.

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
