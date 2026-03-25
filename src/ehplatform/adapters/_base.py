"""
BaseAdapter - tum node adapter'lerinin sistem sahipli temel sinifi.

Algoritma yazari bu sinifa dokunmaz; adapter katmani runtime/UI koprusudur.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Mapping

from algorithms import AlgorithmMetricsSnapshot
from ehplatform.contracts import DataEnvelope, NodeDescriptor


class BaseAdapter(ABC):
    """Tum node adapter'leri bu siniftan turer."""

    descriptor: ClassVar[NodeDescriptor]

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._state: str = "idle"
        self._error_message: str = ""
        self._node_instance_id: str = ""
        self._tick_id: int = 0
        self._variables: dict[str, Any] = {}

        self._frame_count = 0
        self._dropped_frames = 0
        self._last_process_duration_ms = 0.0
        self._average_process_duration_ms = 0.0
        self._last_tick_timestamp = 0.0

    @abstractmethod
    def configure(self, config: dict) -> None:
        ...

    @abstractmethod
    def process(self, inputs: dict[str, DataEnvelope]) -> dict[str, DataEnvelope]:
        ...

    def start(self) -> None:
        self._state = "running"
        self._error_message = ""

    def stop(self) -> None:
        self._state = "idle"

    def reset(self) -> None:
        self._state = "idle"
        self._error_message = ""
        self._frame_count = 0
        self._dropped_frames = 0
        self._last_process_duration_ms = 0.0
        self._average_process_duration_ms = 0.0
        self._last_tick_timestamp = 0.0

    def bind_runtime_identity(self, node_instance_id: str) -> None:
        self._node_instance_id = node_instance_id

    def prepare_tick(self, tick_id: int, variables: Mapping[str, Any] | None = None) -> None:
        self._tick_id = tick_id
        self._variables = dict(variables or {})

    def execute(self, inputs: dict[str, DataEnvelope]) -> dict[str, DataEnvelope]:
        started = time.perf_counter()
        outputs = self.process(inputs)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self._record_metrics(outputs, elapsed_ms)
        return outputs

    def _record_metrics(self, outputs: dict[str, DataEnvelope], elapsed_ms: float) -> None:
        self._frame_count += 1
        self._last_process_duration_ms = elapsed_ms
        self._last_tick_timestamp = time.time()
        if self._frame_count == 1:
            self._average_process_duration_ms = elapsed_ms
        else:
            prev = self._average_process_duration_ms
            self._average_process_duration_ms = prev + (elapsed_ms - prev) / self._frame_count
        if not outputs:
            self._dropped_frames += 1

    @property
    def state(self) -> str:
        return self._state

    @property
    def error_message(self) -> str:
        return self._error_message

    @property
    def node_instance_id(self) -> str:
        return self._node_instance_id

    @property
    def tick_id(self) -> int:
        return self._tick_id

    @property
    def variables(self) -> Mapping[str, Any]:
        return self._variables

    def set_error(self, message: str) -> None:
        self._state = "error"
        self._error_message = message

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    def get_config_value(self, key: str, default=None):
        return self._config.get(key, default)

    def metrics_snapshot(self) -> AlgorithmMetricsSnapshot:
        return AlgorithmMetricsSnapshot(
            frame_count=self._frame_count,
            dropped_frames=self._dropped_frames,
            last_process_duration_ms=self._last_process_duration_ms,
            average_process_duration_ms=self._average_process_duration_ms,
            last_tick_timestamp=self._last_tick_timestamp,
            last_error=self._error_message,
        )


