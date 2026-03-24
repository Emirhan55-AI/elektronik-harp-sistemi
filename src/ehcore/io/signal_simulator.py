"""
SignalSimulator — Test amaçlı rasgele IQ veri üreticisi.
"""

from __future__ import annotations

import numpy as np

from ehcore.contracts import DataEnvelope


class SignalSimulator:
    """Test ve sim modunda rasgele IQ veri üret."""

    def __init__(
        self,
        block_size: int = 256,
        sample_rate: float = 2.4e6,
        center_freq: float = 2.4e9,
    ) -> None:
        """
        Args:
            block_size: Her blok kaç örneklem.
            sample_rate: Örnekleme hızı (Hz).
            center_freq: Merkez frekansı (Hz).
        """
        self.block_size = block_size
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self._block_id = 0

    def generate_block(self) -> DataEnvelope:
        """Rasgele IQ blok oluştur."""
        iq_data = (
            np.random.randn(self.block_size).astype(np.float32) +
            1j * np.random.randn(self.block_size).astype(np.float32)
        ).astype(np.complex64)

        env = DataEnvelope(
            data_type="iq_block",
            payload=iq_data,
            center_freq=self.center_freq,
            sample_rate=self.sample_rate,
        )
        env.metadata["block_id"] = self._block_id

        self._block_id += 1
        return env
