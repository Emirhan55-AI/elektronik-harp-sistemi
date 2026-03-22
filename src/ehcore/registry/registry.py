"""
NodeRegistry — Merkezi adapter kayıt noktası.

Tüm built-in ve plugin adapter'ları bu registry'e kaydolur.
Registry üzerinden palette, runtime ve persistence adapter
bilgisine ulaşır. Switch-case büyümesi olmaz.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ehcore.adapters._base import BaseAdapter
    from ehcore.contracts import NodeDescriptor

logger = logging.getLogger(__name__)


class NodeRegistry:
    """
    Singleton benzeri merkezi adapter kaydı.

    Kullanım:
        @NodeRegistry.register
        class MyAdapter(BaseAdapter):
            descriptor = NodeDescriptor(...)

        # veya programmatik:
        NodeRegistry.register(MyAdapter)

    Sorgulama:
        NodeRegistry.get_all_descriptors()
        NodeRegistry.get_adapter_class("my_node_id")
    """

    _adapters: dict[str, type[BaseAdapter]] = {}

    @classmethod
    def register(cls, adapter_cls: type[BaseAdapter]) -> type[BaseAdapter]:
        """
        Adapter sınıfını kaydet (decorator olarak da kullanılabilir).

        Returns:
            Aynı sınıf (decorator zinciri için).

        Raises:
            ValueError: node_id zaten kayıtlıysa.
        """
        descriptor = adapter_cls.descriptor
        node_id = descriptor.node_id

        if node_id in cls._adapters:
            existing = cls._adapters[node_id]
            if existing is not adapter_cls:
                raise ValueError(
                    f"'{node_id}' zaten kayıtlı: {existing.__name__}. "
                    f"Çakışan: {adapter_cls.__name__}"
                )
            return adapter_cls  # Aynı sınıf tekrar kayıt → sorun yok

        cls._adapters[node_id] = adapter_cls
        logger.debug("Registered adapter: %s (%s)", node_id, adapter_cls.__name__)
        return adapter_cls

    @classmethod
    def unregister(cls, node_id: str) -> None:
        """Adapter kaydını sil (test amaçlı)."""
        cls._adapters.pop(node_id, None)

    @classmethod
    def get_adapter_class(cls, node_id: str) -> type[BaseAdapter] | None:
        """node_id'ye göre adapter sınıfını getir."""
        return cls._adapters.get(node_id)

    @classmethod
    def get_all_descriptors(cls) -> list[NodeDescriptor]:
        """Kayıtlı tüm adapter'ların descriptor'larını listele."""
        return [a.descriptor for a in cls._adapters.values()]

    @classmethod
    def get_categories(cls) -> dict[str, list[NodeDescriptor]]:
        """Descriptor'ları kategoriye göre grupla."""
        categories: dict[str, list[NodeDescriptor]] = {}
        for adapter_cls in cls._adapters.values():
            cat = adapter_cls.descriptor.category
            categories.setdefault(cat, []).append(adapter_cls.descriptor)
        return categories

    @classmethod
    def create_instance(cls, node_id: str) -> BaseAdapter | None:
        """node_id'ye göre yeni adapter örneği oluştur."""
        adapter_cls = cls._adapters.get(node_id)
        if adapter_cls is None:
            return None
        return adapter_cls()

    @classmethod
    def clear(cls) -> None:
        """Tüm kayıtları temizle (test amaçlı)."""
        cls._adapters.clear()

    @classmethod
    def count(cls) -> int:
        """Kayıtlı adapter sayısı."""
        return len(cls._adapters)
