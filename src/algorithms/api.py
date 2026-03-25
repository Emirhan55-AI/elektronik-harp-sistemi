"""
Algorithm kernel API - sistem ile algoritma yazarı arasındaki sabit sözleşme.

Bu modül, algoritma kodunu adapter/runtime/UI katmanlarından ayırır.
Algoritma sahibi yalnızca bu küçük sözleşmeyi bilerek yeni çekirdekler yazabilir.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True, slots=True)
class AlgorithmMetricsSnapshot:
    """Algoritma çağrısı sırasında okunabilen runtime ölçümleri."""

    frame_count: int = 0
    dropped_frames: int = 0
    last_process_duration_ms: float = 0.0
    average_process_duration_ms: float = 0.0
    last_tick_timestamp: float = 0.0
    last_error: str = ""


@dataclass(frozen=True, slots=True)
class AlgorithmContext:
    """Her process çağrısına eşlik eden bağlamsal runtime bilgisi."""

    node_id: str
    tick_id: int
    runtime_state: str
    variables: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    metrics: AlgorithmMetricsSnapshot = field(default_factory=AlgorithmMetricsSnapshot)


@dataclass(slots=True)
class AlgorithmPacket:
    """Algoritmalar arasında akan UI'dan bağımsız veri zarfı."""

    payload: np.ndarray
    timestamp: float = field(default_factory=time.time)
    center_freq: float = 0.0
    sample_rate: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def clone(self, **overrides: Any) -> AlgorithmPacket:
        """Header alanlarını koruyarak yeni paket üret."""
        base = {
            "payload": self.payload,
            "timestamp": self.timestamp,
            "center_freq": self.center_freq,
            "sample_rate": self.sample_rate,
            "metadata": dict(self.metadata),
        }
        base.update(overrides)
        return AlgorithmPacket(**base)


class AlgorithmKernel(ABC):
    """Tüm algoritma çekirdekleri için standart sınıf arayüzü."""

    def __init__(self) -> None:
        self._params: dict[str, Any] = {}

    @abstractmethod
    def configure(self, params: dict[str, Any]) -> None:
        """Algoritma parametrelerini uygula."""
        ...

    def start(self) -> None:
        """Pipeline çalışmaya başlamadan önce çağrılır."""

    @abstractmethod
    def process(
        self,
        inputs: dict[str, AlgorithmPacket],
        context: AlgorithmContext,
    ) -> dict[str, AlgorithmPacket]:
        """Tek işleme adımı."""
        ...

    def stop(self) -> None:
        """Pipeline dururken çağrılır."""

    def reset(self) -> None:
        """Runtime state'i sıfırlar."""



