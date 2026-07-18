# SPDX-License-Identifier: AGPL-3.0-only
"""Writer: intermediate model → manifest.yaml + arrangements/*.json + stems → .feedpak zip (milestone M7).

Emits ``feedpak_version: "1.2.0"``. Output is byte-identical under the ``.feedpak``
(default) and legacy ``.sloppak`` suffixes.
"""
