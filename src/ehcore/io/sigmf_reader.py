"""
SigMF Reader — SigMF formatında IQ verisi okuma.

Desteklenen veri tipleri:
    - ci16_le  : interleaved int16 little-endian → complex64
    - cf32_le  : interleaved float32 little-endian → complex64
    - ci8      : interleaved int8 → complex64

Meta-data JSON dosyasından sample_rate, center_freq vb. okunur.
Dosya blok blok okunarak pipeline'a DataEnvelope olarak beslenir.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from ehcore.contracts import DataEnvelope

logger = logging.getLogger(__name__)

# SigMF dtype → numpy read dtype, bytes per complex sample, normalizer
_DTYPE_MAP: dict[str, tuple[np.dtype, int, float]] = {
    "ci16_le": (np.dtype("<i2"), 4, 32768.0),   # 2 bytes I + 2 bytes Q
    "cf32_le": (np.dtype("<f4"), 8, 1.0),        # 4 bytes I + 4 bytes Q
    "ci8":     (np.dtype("i1"),  2, 128.0),       # 1 byte I + 1 byte Q
}


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
    SigMF okuyucu — ci16_le / cf32_le / ci8 destekli.

    Meta dosyası (.sigmf-meta veya .sigmf-meta.txt) okunur,
    IQ veri dosyası (.sigmf-data) blok blok işlenir.
    """

    def __init__(self) -> None:
        self._meta: dict = {}
        self._data_path: Path | None = None
        self._file = None
        self._sample_rate: float = 0.0
        self._center_freq: float = 0.0
        self._datatype: str = ""
        self._read_dtype: np.dtype = np.dtype("<i2")
        self._bytes_per_sample: int = 4
        self._normalizer: float = 32768.0
        self._offset: int = 0          # Okunan toplam complex sample sayısı
        self._total_samples: int = 0   # Dosyadaki toplam complex sample sayısı
        self._loop: bool = True        # Dosya sonunda başa sar

    def open(self, path: Path) -> None:
        """
        SigMF dosya çiftini aç.

        Args:
            path: .sigmf-data veya .sigmf-meta dosya yolu.
                  Otomatik olarak eşleşen dosyayı bulur.
        """
        path = Path(path)

        # Meta dosyasını bul
        meta_path = self._find_meta(path)
        if meta_path is None:
            raise FileNotFoundError(
                f"SigMF meta dosyası bulunamadı: {path}"
            )

        # Data dosyasını bul
        data_path = self._find_data(path)
        if data_path is None:
            raise FileNotFoundError(
                f"SigMF data dosyası bulunamadı: {path}"
            )

        # Meta parse
        with open(meta_path, "r", encoding="utf-8") as f:
            self._meta = json.load(f)

        global_meta = self._meta.get("global", {})
        captures = self._meta.get("captures", [])

        self._datatype = global_meta.get("core:datatype", "ci16_le")
        self._sample_rate = float(global_meta.get("core:sample_rate", 1.0))

        if captures:
            self._center_freq = float(captures[0].get("core:frequency", 0.0))

        if self._datatype not in _DTYPE_MAP:
            raise ValueError(
                f"Desteklenmeyen SigMF veri tipi: '{self._datatype}'. "
                f"Desteklenen: {list(_DTYPE_MAP.keys())}"
            )

        self._read_dtype, self._bytes_per_sample, self._normalizer = _DTYPE_MAP[self._datatype]

        # Dosya boyutundan toplam sample hesapla
        self._data_path = data_path
        file_size = data_path.stat().st_size
        self._total_samples = file_size // self._bytes_per_sample

        # Dosyayı aç
        self._file = open(data_path, "rb")
        self._offset = 0

        logger.info(
            "SigMF açıldı: %s | %s | Fs=%.1f MHz | Fc=%.1f MHz | %d sample",
            data_path.name, self._datatype,
            self._sample_rate / 1e6,
            self._center_freq / 1e6,
            self._total_samples,
        )

    def read_block(self, block_size: int = 65536) -> DataEnvelope | None:
        """
        Sonraki IQ bloğunu oku.

        Args:
            block_size: Okunacak complex sample sayısı.

        Returns:
            DataEnvelope veya dosya sonuna gelindiyse None (loop kapalıysa).
        """
        if self._file is None:
            return None

        remaining = self._total_samples - self._offset
        if remaining <= 0:
            if self._loop:
                self._file.seek(0)
                self._offset = 0
                remaining = self._total_samples
            else:
                return None

        read_count = min(block_size, remaining)
        # Her complex sample = 2 element (I, Q)
        raw = np.fromfile(
            self._file,
            dtype=self._read_dtype,
            count=read_count * 2,
        )

        if raw.size == 0:
            if self._loop:
                self._file.seek(0)
                self._offset = 0
                return self.read_block(block_size)
            return None

        actual_samples = raw.size // 2

        # I/Q interleaved → complex
        iq = raw[0::2].astype(np.float32) + 1j * raw[1::2].astype(np.float32)
        iq /= self._normalizer  # Normalize

        self._offset += actual_samples

        return DataEnvelope(
            data_type="iq_block",
            payload=iq,
            timestamp=time.time(),
            source_id="sigmf_source",
            center_freq=self._center_freq,
            sample_rate=self._sample_rate,
        )

    def close(self) -> None:
        """Dosyayı kapat."""
        if self._file is not None:
            self._file.close()
            self._file = None
        self._offset = 0

    def get_metadata(self) -> dict:
        """SigMF meta verisini döndür."""
        return {
            "datatype": self._datatype,
            "sample_rate": self._sample_rate,
            "center_freq": self._center_freq,
            "total_samples": self._total_samples,
            **self._meta.get("global", {}),
        }

    @property
    def is_open(self) -> bool:
        return self._file is not None

    @property
    def progress(self) -> float:
        """Okuma ilerlemesi (0.0 - 1.0)."""
        if self._total_samples == 0:
            return 0.0
        return self._offset / self._total_samples

    # ── Yardımcılar ──────────────────────────────────────────────

    @staticmethod
    def _find_meta(path: Path) -> Path | None:
        """Meta dosyasını bul."""
        candidates = [
            path.with_suffix(".sigmf-meta"),
            path.with_suffix(".sigmf-meta.txt"),
            Path(str(path) + ".sigmf-meta"),
        ]
        # Eğer verilen path zaten meta ise
        if "sigmf-meta" in path.name:
            candidates.insert(0, path)

        # .sigmf-data verilmişse, .sigmf-meta'yı dene
        stem = path.name.replace(".sigmf-data", "")
        parent = path.parent
        candidates.extend([
            parent / f"{stem}.sigmf-meta",
            parent / f"{stem}.sigmf-meta.txt",
        ])

        for c in candidates:
            if c.is_file():
                return c
        return None

    @staticmethod
    def _find_data(path: Path) -> Path | None:
        """Data dosyasını bul."""
        candidates = [
            path.with_suffix(".sigmf-data"),
        ]
        if "sigmf-data" in path.name:
            candidates.insert(0, path)

        stem = path.name.replace(".sigmf-meta.txt", "").replace(".sigmf-meta", "")
        parent = path.parent
        candidates.append(parent / f"{stem}.sigmf-data")

        for c in candidates:
            if c.is_file():
                return c
        return None
