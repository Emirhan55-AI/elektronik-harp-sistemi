"""Manifest kesif yardimcilari."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Iterable

from .types import NodeManifest
from .validation import ensure_valid_manifest_collection


def discover_manifests(package_name: str = "ehcore.catalog.manifests") -> tuple[NodeManifest, ...]:
    """Verilen paket altindaki manifest modullerini tara."""
    package = importlib.import_module(package_name)
    manifests: list[NodeManifest] = []

    for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
        module_name = module_info.name.rsplit(".", 1)[-1]
        if module_name.startswith("_"):
            continue

        module = importlib.import_module(module_info.name)
        manifests.extend(_extract_manifests(module))

    manifests.sort(key=lambda manifest: manifest.node_id)
    return ensure_valid_manifest_collection(manifests)


def _extract_manifests(module) -> Iterable[NodeManifest]:
    if hasattr(module, "get_manifests") and callable(module.get_manifests):
        result = module.get_manifests()
        return _coerce_manifests(result)

    if hasattr(module, "MANIFESTS"):
        return _coerce_manifests(module.MANIFESTS)

    return ()


def _coerce_manifests(value) -> tuple[NodeManifest, ...]:
    manifests = tuple(value or ())
    for manifest in manifests:
        if not isinstance(manifest, NodeManifest):
            raise TypeError("Manifest modulu yalnizca NodeManifest nesneleri donmelidir")
    return manifests
