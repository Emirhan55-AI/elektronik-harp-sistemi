"""
SDR Kaynağı Adapter — Simüle veya ZMQ üzerinden IQ verisi üretir.

Bu adaptör, gerçek SDR donanımı kullanmaz. Kaynak tipi config ile
seçilir: "simulator" (varsayılan) veya "zmq".

Gerçek bladeRF entegrasyonu ileride eklenecektir.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np

from ehcore.contracts import (
    DataEnvelope,
    NodeDescriptor,
    PortDef,
    PortType,
)
from ehcore.registry import NodeRegistry

from ._base import BaseAdapter


@NodeRegistry.register
class SourceAdapter(BaseAdapter):
    """SDR Kaynağı — IQ veri üretici (simüle/ZMQ)."""

    descriptor: ClassVar[NodeDescriptor] = NodeDescriptor(
        node_id="sdr_source",
        display_name="SDR Kaynağı",
        category="Kaynaklar",
        description="Simüle veya ZMQ üzerinden IQ verisi üretir.",
        input_ports=(),
        output_ports=(
            PortDef(name="iq_out", port_type=PortType.IQ, display_name="IQ Çıkış"),
        ),
        config_schema={
            "center_freq": {
                "type": "float",
                "default": 100e6,
                "label": "Merkez Frekans (Hz)",
            },
            "sample_rate": {
                "type": "float",
                "default": 2.4e6,
                "label": "Örnekleme Hızı (Hz)",
            },
            "gain": {
                "type": "float",
                "default": 30.0,
                "label": "Kazanç (dB)",
            },
            "block_size": {
                "type": "int",
                "default": 1024,
                "label": "Blok Boyutu",
            },
            "source_type": {
                "type": "str",
                "default": "simulator",
                "label": "Kaynak Tipi",
                "options": ["simulator", "zmq"],
            },
            "num_signals": {
                "type": "int",
                "default": 3,
                "label": "Sinyal Sayısı",
            },
        },
    )

    def __init__(self) -> None:
        super().__init__()
        self._sample_index: int = 0

    def configure(self, config: dict) -> None:
        defaults = self.descriptor.default_config()
        defaults.update(config)
        self._config = defaults
        self._sample_index = 0

    def process(
        self,
        inputs: dict[str, DataEnvelope],
    ) -> dict[str, DataEnvelope]:
        """Tek blok IQ verisi üret."""
        block_size = int(self._config.get("block_size", 1024))
        sample_rate = float(self._config.get("sample_rate", 2.4e6))
        center_freq = float(self._config.get("center_freq", 100e6))
        num_signals = int(self._config.get("num_signals", 3))

        # Simüle sinyal üret
        iq_data = self._generate_simulated(block_size, sample_rate, num_signals)

        envelope = DataEnvelope(
            data_type="iq_block",
            payload=iq_data,
            source_id="sdr_source",
            center_freq=center_freq,
            sample_rate=sample_rate,
        )

        self._sample_index += block_size
        return {"iq_out": envelope}

    def _generate_simulated(
        self, block_size: int, sample_rate: float, num_signals: int
    ) -> np.ndarray:
        """Çoklu sinüs + gürültü simülasyonu."""
        t = np.arange(self._sample_index, self._sample_index + block_size) / sample_rate

        # Gürültü tabanı
        noise = (
            np.random.randn(block_size) + 1j * np.random.randn(block_size)
        ) * 0.01

        signal = noise.astype(np.complex64)

        # Farklı frekanslarda sinüsler ekle
        rng = np.random.RandomState(42)  # Tekrarlanabilir frekanslar
        for i in range(num_signals):
            freq_offset = rng.uniform(-sample_rate / 3, sample_rate / 3)
            amplitude = rng.uniform(0.3, 1.0)
            phase = rng.uniform(0, 2 * np.pi)
            signal += amplitude * np.exp(
                1j * (2 * np.pi * freq_offset * t + phase)
            ).astype(np.complex64)

        return signal
