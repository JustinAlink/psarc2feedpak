# SPDX-License-Identifier: AGPL-3.0-only
"""Neutral intermediate representation: Song / Arrangement / Note / Chord / Beat (milestone M6).

The load-bearing wall between the read side (PSARC/arrangement parsing) and the
write side (.feedpak). Mirrors the target's arrangement dataclasses so the writer
can hand a populated Arrangement straight to the wire encoder.
"""
