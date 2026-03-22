"""
BaseAdapter — Tüm node adaptörlerinin soyut temel sınıfı.

Her adapter:
1. Bir NodeDescriptor taşır (tip bilgisi).
2. configure() ile ayarlanır.
3. process() ile veri işler.
4. start()/stop() ile yaşam döngüsü yönetir.

Adapter, algoritma kodunu doğrudan içermez — ilgili algoritma
modülünü çağırır. Bu katman ince bir köprüdür.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ehcore.contracts import DataEnvelope, NodeDescriptor


class BaseAdapter(ABC):
    """Tüm node adaptörleri bu sınıftan türer."""

    # Alt sınıf bu alanı MUTLAKA tanımlamalı
    descriptor: ClassVar[NodeDescriptor]

    def __init__(self) -> None:
        self._config: dict = {}
        self._state: str = "idle"  # "idle" | "running" | "error"
        self._error_message: str = ""

    # ── Yaşam Döngüsü ───────────────────────────────────────────

    @abstractmethod
    def configure(self, config: dict) -> None:
        """
        Node ayarlarını uygula.
        config, NodeDescriptor.config_schema'ya uygun olmalı.
        """
        ...

    @abstractmethod
    def process(
        self,
        inputs: dict[str, DataEnvelope],
    ) -> dict[str, DataEnvelope]:
        """
        Tek bir işleme adımı.

        Args:
            inputs: Port adı → DataEnvelope eşlemesi.

        Returns:
            Çıkış portları → DataEnvelope eşlemesi.
        """
        ...

    def start(self) -> None:
        """Pipeline başlatıldığında çağrılır."""
        self._state = "running"
        self._error_message = ""

    def stop(self) -> None:
        """Pipeline durdurulduğunda çağrılır."""
        self._state = "idle"

    def reset(self) -> None:
        """Sıfırlama — state ve hatayı temizle."""
        self._state = "idle"
        self._error_message = ""

    # ── Durum Bilgisi ────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    @property
    def error_message(self) -> str:
        return self._error_message

    def set_error(self, message: str) -> None:
        """Node'u hata durumuna düşür."""
        self._state = "error"
        self._error_message = message

    # ── Config Erişimi ───────────────────────────────────────────

    @property
    def config(self) -> dict:
        return self._config

    def get_config_value(self, key: str, default=None):
        """Config'den değer oku, yoksa default döndür."""
        return self._config.get(key, default)
