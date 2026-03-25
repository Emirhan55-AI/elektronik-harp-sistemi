"""
DataEnvelope — Tüm node'lar arasında akan ortak veri modeli.

Desteklenen data_type'lar:
    - "iq_block"       : Ham IQ verisi (complex64/complex128)
    - "fft_frame"      : Tek FFT çerçevesi (float32/float64, dB veya lineer)
    - "waterfall_row"  : Waterfall için tek satır (float32)
    - "detections"     : Tespit listesi (structured array veya dict listesi)

Ortak metadata alanları her zarf için zorunludur; ek bilgiler
`metadata` dict'ine konulabilir.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# Geçerli veri tipleri
VALID_DATA_TYPES = frozenset({
    "iq_block",
    "fft_frame",
    "spectrogram",
    "waterfall_row",
    "detections",
    "detection_list",
})


@dataclass(slots=True)
class DataEnvelope:
    """Pipeline'da node'lar arası akan veri zarfı."""

    # ── Zorunlu alanlar ──────────────────────────────────────────
    data_type: str                          # VALID_DATA_TYPES'tan biri
    payload: np.ndarray                     # Asıl veri

    # ── Ortak metadata ───────────────────────────────────────────
    timestamp: float = field(default_factory=time.time)
    source_id: str = ""                     # Üreten node'un ID'si
    center_freq: float = 0.0                # Hz
    sample_rate: float = 0.0                # Hz
    dtype: str = ""                         # "complex64", "float32", …
    shape: tuple[int, ...] = ()             # payload.shape kopyası

    # ── Ek metadata ──────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Otomatik doldurma ve doğrulama."""
        if self.data_type not in VALID_DATA_TYPES:
            raise ValueError(
                f"Geçersiz data_type: '{self.data_type}'. "
                f"Geçerli tipler: {VALID_DATA_TYPES}"
            )

        # payload'dan otomatik türet (eğer boş bırakıldıysa)
        if not self.dtype:
            self.dtype = str(self.payload.dtype)
        if not self.shape:
            self.shape = tuple(self.payload.shape)

    # ── Yardımcı metodlar ────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict üret (payload hariç)."""
        return {
            "data_type": self.data_type,
            "timestamp": self.timestamp,
            "source_id": self.source_id,
            "center_freq": self.center_freq,
            "sample_rate": self.sample_rate,
            "dtype": self.dtype,
            "shape": list(self.shape),
            "metadata": self.metadata,
        }

    @property
    def size_bytes(self) -> int:
        """Payload'ın byte boyutu."""
        return self.payload.nbytes

    def clone_header(self, **overrides: Any) -> DataEnvelope:
        """Payload'sız kopyalama (yeni payload ile doldurulacak)."""
        base = {
            "data_type": self.data_type,
            "timestamp": self.timestamp,
            "source_id": self.source_id,
            "center_freq": self.center_freq,
            "sample_rate": self.sample_rate,
            "metadata": dict(self.metadata),
        }
        base.update(overrides)
        # payload zorunlu — override'da verilmeli
        return DataEnvelope(**base)  # type: ignore[arg-type]


