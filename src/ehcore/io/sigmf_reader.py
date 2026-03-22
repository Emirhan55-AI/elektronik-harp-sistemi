"""
SigMF Reader — SigMF formatında veri okuma genişleme noktası.

Bu modül şimdilik bir stub'dır. İleride SigMF meta-data parsing
ve IQ data okuma ekleneceği varsayılmaktadır.

BaseReader ABC tanımlar — SigMF, WAV, raw IQ okuyucuları
aynı arayüzle eklenir.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ehcore.contracts import DataEnvelope


class BaseReader(ABC):
    """Dosya tabanlı veri okuyucu arayüzü."""

    @abstractmethod
    def open(self, path: Path) -> None:
        """Dosyayı aç ve metadata oku."""
        ...

    @abstractmethod
    def read_block(self, block_size: int = 1024) -> DataEnvelope | None:
        """
        Sonraki blok IQ verisini oku.

        Returns:
            DataEnvelope veya dosya sonuna gelindiyse None.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Dosyayı kapat."""
        ...

    @abstractmethod
    def get_metadata(self) -> dict:
        """Dosya metadata'sını döndür."""
        ...


class SigMFReader(BaseReader):
    """
    SigMF okuyucu — STUB.

    İleride sigmf paketi ile meta-data parsing ve
    IQ binary okuma eklenecek.
    """

    def open(self, path: Path) -> None:
        raise NotImplementedError(
            "SigMF okuyucu henüz implemente edilmedi. "
            "İleride sigmf paketi entegre edilecek."
        )

    def read_block(self, block_size: int = 1024) -> DataEnvelope | None:
        raise NotImplementedError

    def close(self) -> None:
        pass

    def get_metadata(self) -> dict:
        raise NotImplementedError
