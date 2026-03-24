"""
STFT İşleyici Adaptörü — Katman A: Ön İşleme.

IQ bloğunu alır ve Welch PSD üretir.

Algoritma kodu ehcore.algorithms.dsp.stft modülündedir.
Bu adapter ince bir köprüdür.
"""

from __future__ import annotations

from typing import ClassVar

from ehcore.algorithms.dsp import compute_psd
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
        description="IQ verisinden Welch PSD hesaplar. DC ofset temizler.",
        input_ports=(
            PortDef(name="iq_in", port_type=PortType.IQ, display_name="IQ Giriş"),
        ),
        output_ports=(
            PortDef(name="fft_out", port_type=PortType.FFT, display_name="PSD Çıkış"),
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
        """IQ bloğu → PSD."""
        iq_envelope = inputs.get("iq_in")
        if iq_envelope is None:
            return {}

        fft_size = int(self._config.get("fft_size", 1024))
        window = str(self._config.get("window", "hann"))
        remove_dc = bool(self._config.get("remove_dc", True))

        iq_data = iq_envelope.payload
        _freqs, psd_db = compute_psd(
            iq_data,
            fft_size=fft_size,
            sample_rate=iq_envelope.sample_rate,
            window=window,
            remove_dc=remove_dc,
        )

        # FFT / PSD çıkışı
        fft_envelope = iq_envelope.clone_header(
            data_type="fft_frame",
            payload=psd_db,
        )
        fft_envelope.metadata["fft_size"] = fft_size

        return {
            "fft_out": fft_envelope,
        }
