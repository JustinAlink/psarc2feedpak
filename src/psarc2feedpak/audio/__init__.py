# SPDX-License-Identifier: AGPL-3.0-only
"""Audio normalization: decoded audio → OGG Vorbis ``stems/full.ogg`` (milestone M3).

Shells out to an external decoder (e.g. vgmstream/ffmpeg) that the user has
installed; ships no codecs and decrypts nothing.
"""
