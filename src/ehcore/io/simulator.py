"""
SignalSimulator — Test amaçlı simüle IQ sinyal üretici.

Çoklu sinüs + gürültü üretir. Çıktı: DataEnvelope(data_type="iq_block").
SourceAdapter bu sınıfı dolaylı olarak kullanabilir veya doğrudan test
edebilirsiniz.
"""

from __future__ import annotations

import numpy as np

from ehcore.contracts import DataEnvelope


class SignalSimulator:
    """
    Yapılandırılabilir simüle IQ sinyal üretici.

    Parametreler:
        sample_rate: Örnekleme hızı (Hz).
        center_freq: Merkez frekans (Hz).
        block_size: Her çağrıda üretilecek örnek sayısı.
        num_signals: Eklenecek sinüs sinyali sayısı.
        noise_level: Gürültü standart sapması.
        seed: Rastgelelik tohumu (tekrarlanabilirlik için).
    """

    def __init__(
        self,
        sample_rate: float = 2.4e6,
        center_freq: float = 100e6,
        block_size: int = 1024,
        num_signals: int = 3,
        noise_level: float = 0.01,
        seed: int = 42,
    ) -> None:
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.block_size = block_size
        self.num_signals = num_signals
        self.noise_level = noise_level
        self._rng = np.random.RandomState(seed)
        self._sample_index: int = 0

        # Sinyal parametreleri (sabit, seed ile belirlenir)
        self._signal_params = self._generate_signal_params()

    def _generate_signal_params(self) -> list[dict]:
        """Her sinüs sinyalinin parametrelerini üret."""
        params = []
        for _ in range(self.num_signals):
            params.append({
                "freq_offset": self._rng.uniform(
                    -self.sample_rate / 3, self.sample_rate / 3
                ),
                "amplitude": self._rng.uniform(0.3, 1.0),
                "phase": self._rng.uniform(0, 2 * np.pi),
            })
        return params

    def generate_block(self) -> DataEnvelope:
        """Tek blok IQ verisi üret ve DataEnvelope olarak döndür."""
        t = (
            np.arange(self._sample_index, self._sample_index + self.block_size)
            / self.sample_rate
        )

        # Gürültü tabanı
        noise = (
            np.random.randn(self.block_size)
            + 1j * np.random.randn(self.block_size)
        ) * self.noise_level

        signal = noise.astype(np.complex64)

        # Sinüsler ekle
        for p in self._signal_params:
            signal += (
                p["amplitude"]
                * np.exp(1j * (2 * np.pi * p["freq_offset"] * t + p["phase"]))
            ).astype(np.complex64)

        self._sample_index += self.block_size

        return DataEnvelope(
            data_type="iq_block",
            payload=signal,
            source_id="simulator",
            center_freq=self.center_freq,
            sample_rate=self.sample_rate,
        )

    def reset(self) -> None:
        """Sayacı sıfırla."""
        self._sample_index = 0
