# Synthetic fixtures

Everything in this directory is **synthetic** — generated from hard-coded integer
literals and in-memory 1×1 PNGs by a committed generator script (`make_fixtures.py`,
added with milestone M1). It contains **no third-party bytes**: no real `.psarc`,
`.sng`, audio, or album art; no base64 of a real file; no "minimal real header
from online."

Real, user-owned files used for debugging live **outside this repo** (e.g.
`~/psarc-lab/`) and must never be committed. See [../../../CONTENT_POLICY.md](../../../CONTENT_POLICY.md).
