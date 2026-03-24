"""
ehcore.adapters — Node adaptörleri paketi.

Bu modül import edildiğinde built-in adaptörler otomatik olarak
NodeRegistry'ye kaydolur (@NodeRegistry.register decorator'ı ile).
"""

from ._base import BaseAdapter
from .sigmf_source_adapter import SigMFSourceAdapter
from .stft_adapter import STFTAdapter
from .cfar_adapter import CFARAdapter
from .stability_adapter import StabilityFilterAdapter

__all__ = [
    "BaseAdapter",
    "SigMFSourceAdapter",
    "STFTAdapter",
    "CFARAdapter",
    "StabilityFilterAdapter",
]
