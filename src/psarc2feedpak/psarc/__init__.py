# SPDX-License-Identifier: AGPL-3.0-only
"""Clean-room PSARC container reader — TOC, block table, zlib inflate (milestone M1).

Implemented from the public PSARC container layout. Reads the archive directory
and decompresses member blocks; it does not decrypt protected inner files.
"""
