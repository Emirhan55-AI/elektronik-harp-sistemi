"""
FFT İşleyici Adapter — IQ bloğunu FFT çerçevesine dönüştürür.

Bu adaptör `ehcore.algorithms.dsp.fft` modülündeki compute_fft
fonksiyonunu çağırır. Kendi içinde FFT kodu YOKTUR — sadece köprü.
"""

from __future__ import annotations

from typing import ClassVar

from ehcore.algorithms.dsp import compute_fft
from ehcore.contracts import (
    DataEnvelope,
    NodeDescriptor,
    PortDef,
    PortType,
)
from ehcore.registry import NodeRegistry

from ._base import BaseAdapter


@NodeRegistry.register
class FFTAdapter(BaseAdapter):
    """FFT İşleyici — IQ → FFT dönüştürücü."""

    descriptor: ClassVar[NodeDescriptor] = NodeDescriptor(
        node_id="fft_processor",
        display_name="FFT İşleyici",
        category="İşleyiciler",
        description="IQ verisinden FFT çerçevesi hesaplar.",
        input_ports=(
            PortDef(name="iq_in", port_type=PortType.IQ, display_name="IQ Giriş"),
        ),
        output_ports=(
            PortDef(name="fft_out", port_type=PortType.FFT, display_name="FFT Çıkış"),
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
                "options": [256, 512, 1024, 2048, 4096],
            },
            "window": {
                "type": "str",
                "default": "hann",
                "label": "Pencere Fonksiyonu",
                "options": ["hann", "hamming", "blackman", "none"],
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
        """IQ bloğu → FFT çerçevesi + waterfall satırı."""
        iq_envelope = inputs.get("iq_in")
        if iq_envelope is None:
            return {}

        fft_size = int(self._config.get("fft_size", 1024))
        window = str(self._config.get("window", "hann"))

        # Algoritma çağrısı — adaptör FFT kodunu İÇERMEZ
        fft_db = compute_fft(iq_envelope.payload, fft_size=fft_size, window=window)

        # FFT çıkışı
        fft_envelope = iq_envelope.clone_header(
            data_type="fft_frame",
            payload=fft_db,
        )

        # Waterfall satırı (aynı veri, farklı tip)
        waterfall_envelope = iq_envelope.clone_header(
            data_type="waterfall_row",
            payload=fft_db.copy(),
        )

        return {
            "fft_out": fft_envelope,
            "waterfall_out": waterfall_envelope,
        }
