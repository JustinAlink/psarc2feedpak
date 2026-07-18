# Content Policy

This repository contains **no copyrighted content, ever** — not one real byte,
not even "one small example." Enforced rules:

1. **No copyrighted inputs or outputs** are ever committed: no `.psarc`, `.sng`,
   audio (`.wem/.ogg/.mp3/.wav/...`), album art, game assets, or built packs.
   A single real file in git *history* is exactly what a takedown targets, and
   `git rm` does not purge history.
2. **Tests use synthetic fixtures only.** `tests/fixtures/synthetic/` is
   generated from hard-coded integer literals + in-memory 1×1 PNGs by a
   committed generator script. It contains **no third-party bytes** — no base64
   of a real file, no "minimal real header from online."
3. **The tool performs no decryption.** It converts already-unpacked
   arrangements; it does not bypass access controls, and it never fetches or
   runs a decryptor.
4. **CI enforces this** (`.github/workflows/ci.yml` → `no-binary-content`), and
   a matching pre-commit check should trip the wire locally.
5. **Real-file debugging lives outside the repo** (e.g. `~/psarc-lab/`), never
   `git add -f`.

If a committed synthetic PNG is ever unavoidable, allowlist that one exact path
and have CI verify it by hash.
