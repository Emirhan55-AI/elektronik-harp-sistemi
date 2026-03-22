"""
ehcore.adapters — Node adaptörleri paketi.

Bu modül import edildiğinde built-in adaptörler otomatik olarak
NodeRegistry'ye kaydolur (@NodeRegistry.register decorator'ı ile).
"""

from ._base import BaseAdapter
from .source_adapter import SourceAdapter
from .fft_adapter import FFTAdapter
from .viewer_adapter import ViewerAdapter

__all__ = [
    "BaseAdapter",
    "SourceAdapter",
    "FFTAdapter",
    "ViewerAdapter",
]
