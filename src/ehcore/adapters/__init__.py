"""
ehcore.adapters - sistem sahipli adapter bootstrap paketi.

Built-in bloklar merkezi manifest katalogundan registry'ye kaydedilir.
Eski adapter dosyalari uyumluluk amaciyla repoda kalabilir; otomatik bootstrap
manifest tabani uzerinden calisir.
"""

from ehcore.catalog.bootstrap import register_builtin_manifests

from ._base import BaseAdapter
from .manifest_backed import ManifestBackedAdapter

register_builtin_manifests()

__all__ = [
    "BaseAdapter",
    "ManifestBackedAdapter",
]
