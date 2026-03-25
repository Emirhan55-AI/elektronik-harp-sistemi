"""Yerlesik blok manifestlerinin uyumluluk katmani."""

from __future__ import annotations

from .discovery import discover_manifests


BUILTIN_NODE_MANIFESTS = discover_manifests()


