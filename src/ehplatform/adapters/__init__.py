"""
Sistem sahipli adapter bootstrap paketi.

Built-in bloklar merkezi manifest katalogundan registry'ye kaydedilir.
Runtime manifest tabanli bootstrap uzerinden calisir.
"""

from ehplatform.catalog.bootstrap import register_builtin_manifests

from ._base import BaseAdapter
from .manifest_backed import ManifestBackedAdapter

register_builtin_manifests()

__all__ = [
    "BaseAdapter",
    "ManifestBackedAdapter",
]
