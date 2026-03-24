"""
NodeRegistry - merkezi adapter ve manifest kayit noktasi.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ehcore.catalog.types import NodeManifest
from ehcore.catalog.validation import ensure_valid_manifest

if TYPE_CHECKING:
    from ehcore.adapters._base import BaseAdapter
    from ehcore.contracts import NodeDescriptor

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Merkezi adapter ve manifest kaydi."""

    _adapters: dict[str, type["BaseAdapter"]] = {}
    _manifests: dict[str, NodeManifest] = {}

    @classmethod
    def register(cls, adapter_cls: type["BaseAdapter"]) -> type["BaseAdapter"]:
        descriptor = adapter_cls.descriptor
        node_id = descriptor.node_id

        if node_id in cls._adapters:
            existing = cls._adapters[node_id]
            if existing is not adapter_cls:
                raise ValueError(
                    f"'{node_id}' zaten kayitli: {existing.__name__}. "
                    f"Cakisan: {adapter_cls.__name__}"
                )
            return adapter_cls

        manifest = getattr(adapter_cls, "manifest", None)
        if isinstance(manifest, NodeManifest):
            cls._manifests[node_id] = manifest
        elif node_id not in cls._manifests:
            cls._manifests[node_id] = NodeManifest.from_descriptor(descriptor)

        cls._adapters[node_id] = adapter_cls
        logger.debug("Registered adapter: %s (%s)", node_id, adapter_cls.__name__)
        return adapter_cls

    @classmethod
    def register_manifest(cls, manifest: NodeManifest) -> type["BaseAdapter"]:
        ensure_valid_manifest(manifest)
        existing = cls._manifests.get(manifest.node_id)
        if existing == manifest and manifest.node_id in cls._adapters:
            return cls._adapters[manifest.node_id]

        from ehcore.adapters.manifest_backed import build_manifest_adapter_class

        adapter_cls = build_manifest_adapter_class(manifest)
        cls._manifests[manifest.node_id] = manifest
        return cls.register(adapter_cls)

    @classmethod
    def unregister(cls, node_id: str) -> None:
        cls._adapters.pop(node_id, None)
        cls._manifests.pop(node_id, None)

    @classmethod
    def get_adapter_class(cls, node_id: str) -> type["BaseAdapter"] | None:
        return cls._adapters.get(node_id)

    @classmethod
    def get_manifest(cls, node_id: str) -> NodeManifest | None:
        return cls._manifests.get(node_id)

    @classmethod
    def get_all_descriptors(cls) -> list["NodeDescriptor"]:
        return [adapter.descriptor for adapter in cls._adapters.values()]

    @classmethod
    def get_all_manifests(cls) -> list[NodeManifest]:
        return list(cls._manifests.values())

    @classmethod
    def get_categories(cls) -> dict[str, list["NodeDescriptor"]]:
        categories: dict[str, list["NodeDescriptor"]] = {}
        for adapter_cls in cls._adapters.values():
            cat = adapter_cls.descriptor.category
            categories.setdefault(cat, []).append(adapter_cls.descriptor)
        return categories

    @classmethod
    def create_instance(cls, node_id: str) -> "BaseAdapter" | None:
        adapter_cls = cls._adapters.get(node_id)
        if adapter_cls is None:
            return None
        return adapter_cls()

    @classmethod
    def clear(cls) -> None:
        cls._adapters.clear()
        cls._manifests.clear()

    @classmethod
    def count(cls) -> int:
        return len(cls._adapters)
