"""
STFT İşleyici Adaptörü — Katman A: Ön İşleme.

IQ bloğunu alır, STFT uygular ve 3 farklı çıkış üretir:
  1. fft_out   : Welch PSD (tek satır, dB) → Spektrum grafiği
  2. spectrogram_out : 2D spektrogram (dB) → Waterfall/Şelale
  3. waterfall_out   : Son PSD satırı → Waterfall widget

Algoritma kodu ehcore.algorithms.dsp.stft modülündedir.
Bu adapter ince bir köprüdür.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np

from ehcore.algorithms.dsp import compute_stft, compute_psd
from ehcore.contracts import (
    DataEnvelope,
    NodeDescriptor,
    PortDef,
    PortType,
)
from ehcore.registry import NodeRegistry

from ._base import BaseAdapter


@NodeRegistry.register
class STFTAdapter(BaseAdapter):
    """STFT İşleyici — IQ → Frekans Düzlemi dönüştürücü."""

    descriptor: ClassVar[NodeDescriptor] = NodeDescriptor(
        node_id="stft_processor",
        display_name="STFT İşleyici",
        category="Ön İşleme",
        description="IQ verisinden STFT/Welch PSD hesaplar. DC ofset temizler.",
        input_ports=(
            PortDef(name="iq_in", port_type=PortType.IQ, display_name="IQ Giriş"),
        ),
        output_ports=(
            PortDef(name="fft_out", port_type=PortType.FFT, display_name="PSD Çıkış"),
            PortDef(
                name="spectrogram_out",
                port_type=PortType.SPECTROGRAM,
                display_name="Spektrogram Çıkış",
            ),
            PortDef(
                name="waterfall_out",
                port_type=PortType.WATERFALL,
                display_name="Waterfall Çıkış",
            ),
        ),
        config_schema={
            "fft_size": {
                "type": "int",
                "default": 1024,
                "label": "FFT Boyutu",
                "options": [256, 512, 1024, 2048, 4096, 8192],
            },
            "window": {
                "type": "str",
                "default": "hann",
                "label": "Pencere Fonksiyonu",
                "options": ["hann", "hamming", "blackman", "none"],
            },
            "overlap_ratio": {
                "type": "float",
                "default": 0.5,
                "label": "Örtüşme Oranı",
            },
            "remove_dc": {
                "type": "bool",
                "default": True,
                "label": "DC Ofset Temizle",
            },
        },
    )

    def configure(self, config: dict) -> None:
        defaults = self.descriptor.default_config()
        defaults.update(config)
        self._config = defaults

    def process(
        self,
        inputs: dict[str, DataEnvelope],
    ) -> dict[str, DataEnvelope]:
        """IQ bloğu → PSD + Spektrogram + Waterfall satırı."""
        iq_envelope = inputs.get("iq_in")
        if iq_envelope is None:
            return {}

        fft_size = int(self._config.get("fft_size", 1024))
        window = str(self._config.get("window", "hann"))
        overlap = float(self._config.get("overlap_ratio", 0.5))
        remove_dc = bool(self._config.get("remove_dc", True))

        hop_size = max(1, int(fft_size * (1.0 - overlap)))

        iq_data = iq_envelope.payload

        # STFT hesapla → 2D spektrogram
        spectrogram_db, freqs = compute_stft(
            iq_data,
            fft_size=fft_size,
            hop_size=hop_size,
            window=window,
            remove_dc=remove_dc,
        )

        # Welch PSD → tek satır (segmentlerin ortalaması)
        psd_db = np.mean(spectrogram_db, axis=0)

        # FFT / PSD çıkışı
        fft_envelope = iq_envelope.clone_header(
            data_type="fft_frame",
            payload=psd_db,
        )

        # Spektrogram çıkışı
        spec_envelope = iq_envelope.clone_header(
            data_type="spectrogram",
            payload=spectrogram_db,
        )

        # Waterfall satırı (son PSD)
        waterfall_envelope = iq_envelope.clone_header(
            data_type="waterfall_row",
            payload=psd_db.copy(),
        )

        return {
            "fft_out": fft_envelope,
            "spectrogram_out": spec_envelope,
            "waterfall_out": waterfall_envelope,
        }
