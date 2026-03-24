"""Katalog bootstrap yardimcilari."""

from __future__ import annotations

from ehcore.registry import NodeRegistry

from .discovery import discover_manifests


def register_builtin_manifests() -> int:
    """Built-in manifestleri registry'ye kaydet."""
    count = 0
    for manifest in discover_manifests():
        NodeRegistry.register_manifest(manifest)
        count += 1
    return count
