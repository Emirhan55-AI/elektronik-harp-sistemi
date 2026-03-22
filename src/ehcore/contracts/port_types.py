"""
PortType enum ve PortDef — Node portları için tip sistemi.

Her port bir PortType taşır. Bağlantı kurulurken uyumluluk
matrisi kontrol edilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class PortType(Enum):
    """Node port veri tipleri."""
    IQ = auto()          # Ham IQ verisi (complex)
    FFT = auto()         # FFT çerçevesi (float, dB)
    WATERFALL = auto()   # Waterfall satırı
    DETECTIONS = auto()  # Tespit listesi
    ANY = auto()         # Herhangi bir tip kabul eder

    def display_name(self) -> str:
        """Türkçe görünen ad."""
        _names = {
            PortType.IQ: "IQ",
            PortType.FFT: "FFT",
            PortType.WATERFALL: "Waterfall",
            PortType.DETECTIONS: "Tespitler",
            PortType.ANY: "Genel",
        }
        return _names.get(self, self.name)


# ── Uyumluluk Matrisi ──────────────────────────────────────────
# Hangi çıkış tipi hangi giriş tipine bağlanabilir?
# ANY her şeyi kabul eder; spesifik tipler eşleşmeli.

_COMPATIBILITY: dict[PortType, frozenset[PortType]] = {
    PortType.IQ:         frozenset({PortType.IQ, PortType.ANY}),
    PortType.FFT:        frozenset({PortType.FFT, PortType.ANY}),
    PortType.WATERFALL:  frozenset({PortType.WATERFALL, PortType.ANY}),
    PortType.DETECTIONS: frozenset({PortType.DETECTIONS, PortType.ANY}),
    PortType.ANY:        frozenset({
        PortType.IQ, PortType.FFT, PortType.WATERFALL,
        PortType.DETECTIONS, PortType.ANY,
    }),
}


def check_port_compatibility(
    output_type: PortType,
    input_type: PortType,
) -> bool:
    """Çıkış portu tipinin giriş portu tipine bağlanıp bağlanamayacağını kontrol et."""
    # ANY giriş her şeyi kabul eder
    if input_type == PortType.ANY:
        return True
    return input_type in _COMPATIBILITY.get(output_type, frozenset())


@dataclass(frozen=True, slots=True)
class PortDef:
    """Tek bir port tanımı (input veya output)."""

    name: str                # Port benzersiz adı (İngilizce): "iq_in", "fft_out"
    port_type: PortType      # Veri tipi
    display_name: str = ""   # Türkçe görünen ad (opsiyonel)
    required: bool = True    # Input portlar için: bağlanması zorunlu mu?

    def __post_init__(self) -> None:
        if not self.display_name:
            # frozen=True olduğu için object.__setattr__ kullanılmalı
            object.__setattr__(self, "display_name", self.port_type.display_name())
