"""
PipelineEngine - headless pipeline yurutme motoru.

Topological sort sirasina gore node'lari yurutur.
Her node'un process() cagrilir, cikti sonraki node'a aktarilir.
Node bazinda hata yakalama vardir; hatali node atlanir, pipeline durmaz.
"""

from __future__ import annotations

from collections import deque
import copy
import logging
import threading
import time
from typing import Any, Callable

from ehplatform.adapters._base import BaseAdapter
from ehplatform.contracts import DataEnvelope
from ehplatform.registry import NodeRegistry

from .graph import PipelineGraph
from .scheduler import topological_sort
from .validator import Severity, validate_pipeline
from .variables import VariableResolutionError, resolve_config

logger = logging.getLogger(__name__)


class PipelineEngine:
    """
    Headless pipeline yurutme motoru.

    Kullanim:
        engine = PipelineEngine(graph)
        engine.start()
        engine.stop()
    """

    def __init__(
        self,
        graph: PipelineGraph,
        on_error: Callable[[str, str], None] | None = None,
        on_state_change: Callable[[str], None] | None = None,
        tick_interval: float = 0.05,
    ) -> None:
        self._graph = graph
        self._on_error = on_error
        self._on_state_change = on_state_change
        self._tick_interval = tick_interval

        self._adapters: dict[str, BaseAdapter] = {}
        self._execution_order: list[str] = []
        self._state: str = "idle"
        self._tick_counter: int = 0
        self._variables: dict[str, object] = dict(graph.variables)
        self._probe_history: dict[str, dict[str, deque[dict[str, Any]]]] = {}
        self._probe_history_limit = 12

        self._thread: threading.Thread | None = None
        self._running = threading.Event()

        # UI tarafinin okuyacagi son ciktilar.
        self.last_outputs: dict[str, dict[str, DataEnvelope]] = {}

    def start(self) -> list[str]:
        """Pipeline'i dogrula, adapter'lari olustur ve calistir."""
        messages = validate_pipeline(self._graph)
        errors = [message for message in messages if message.severity == Severity.ERROR]
        if errors:
            return [message.message for message in errors]

        self._execution_order = topological_sort(self._graph)
        self._adapters.clear()
        self._probe_history.clear()

        for node_id in self._execution_order:
            node = self._graph.get_node(node_id)
            if node is None:
                continue

            adapter = NodeRegistry.create_instance(node.node_type_id)
            if adapter is None:
                return [f"Adapter olusturulamadi: {node.node_type_id}"]

            try:
                adapter.configure(resolve_config(node.config, self._variables))
                adapter.bind_runtime_identity(node.instance_id)
                adapter.start()
            except VariableResolutionError as exc:
                return [f"Degisken cozumleme hatasi ({node.node_type_id}): {exc}"]
            except Exception as exc:
                return [f"Adapter yapilandirma hatasi ({node.node_type_id}): {exc}"]

            self._adapters[node_id] = adapter

        self._running.set()
        self._set_state("running")
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="pipeline-engine",
        )
        self._thread.start()
        logger.info("Pipeline baslatildi (%d node).", len(self._execution_order))
        return []

    def stop(self) -> None:
        """Pipeline'i durdur."""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

        self.last_outputs = {}
        self._probe_history.clear()

        for adapter in self._adapters.values():
            try:
                adapter.stop()
            except Exception:
                pass

        self._set_state("idle")
        logger.info("Pipeline durduruldu.")

    def reset(self) -> None:
        """Durdur ve sifirla."""
        self.stop()
        for adapter in self._adapters.values():
            try:
                adapter.reset()
            except Exception:
                pass
        self._adapters.clear()
        self._execution_order.clear()
        self._probe_history.clear()

    @property
    def state(self) -> str:
        return self._state

    @property
    def graph(self) -> PipelineGraph:
        return self._graph

    @property
    def adapters(self) -> dict[str, BaseAdapter]:
        return self._adapters

    @property
    def probe_history(self) -> dict[str, dict[str, tuple[dict[str, Any], ...]]]:
        return {
            node_id: {
                port_name: tuple(history)
                for port_name, history in port_map.items()
            }
            for node_id, port_map in self._probe_history.items()
        }

    def get_probe_history(self, node_id: str, limit: int = 12) -> list[dict[str, Any]]:
        port_map = self._probe_history.get(node_id, {})
        entries = [
            dict(entry)
            for history in port_map.values()
            for entry in history
        ]
        entries.sort(key=lambda item: float(item.get("timestamp", 0.0)), reverse=True)
        return entries[:limit]

    def _run_loop(self) -> None:
        while self._running.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("Pipeline tick hatasi")
                self._set_state("error")
                self._running.clear()
                return

            time.sleep(self._tick_interval)

    def _tick(self) -> None:
        outputs: dict[str, dict[str, DataEnvelope]] = {}
        self._tick_counter += 1

        for node_id in self._execution_order:
            adapter = self._adapters.get(node_id)
            if adapter is None or adapter.state == "error":
                continue

            inputs: dict[str, DataEnvelope] = {}
            for edge in self._graph.get_edges_to(node_id):
                src_outputs = outputs.get(edge.source_node_id, {})
                if edge.source_port in src_outputs:
                    inputs[edge.target_port] = src_outputs[edge.source_port]

            try:
                adapter.prepare_tick(self._tick_counter, self._variables)
                result = adapter.execute(inputs)
                outputs[node_id] = result or {}
                self._record_probe_outputs(node_id, outputs[node_id])
            except Exception as exc:
                error_msg = f"[{node_id}] Isleme hatasi: {exc}"
                logger.error(error_msg)
                adapter.set_error(str(exc))
                if self._on_error:
                    self._on_error(node_id, error_msg)

        self.last_outputs = copy.copy(outputs)

    def _set_state(self, new_state: str) -> None:
        self._state = new_state
        if self._on_state_change:
            self._on_state_change(new_state)

    def update_node_config(self, instance_id: str, new_config: dict) -> None:
        adapter = self._adapters.get(instance_id)
        if adapter is not None:
            adapter.configure(resolve_config(new_config, self._variables))

    def update_variables(self, variables: dict[str, object]) -> list[str]:
        self._variables = dict(variables)
        errors: list[str] = []
        for node_id in self._execution_order:
            node = self._graph.get_node(node_id)
            adapter = self._adapters.get(node_id)
            if node is None or adapter is None:
                continue
            try:
                adapter.configure(resolve_config(node.config, self._variables))
            except Exception as exc:
                errors.append(f"[{node.node_type_id}] Degisken guncelleme hatasi: {exc}")
        return errors

    def single_tick(self) -> dict[str, dict[str, DataEnvelope]]:
        """
        Tek bir tick calistir ve ciktlari dondur.
        Pipeline'in start() ile baslatilmis olmasi gerekmez.
        """
        if not self._adapters:
            self._execution_order = topological_sort(self._graph)
            for node_id in self._execution_order:
                node = self._graph.get_node(node_id)
                if node is None:
                    continue
                adapter = NodeRegistry.create_instance(node.node_type_id)
                if adapter is None:
                    continue
                adapter.configure(resolve_config(node.config, self._variables))
                adapter.bind_runtime_identity(node.instance_id)
                self._adapters[node_id] = adapter

        outputs: dict[str, dict[str, DataEnvelope]] = {}
        self._tick_counter += 1
        for node_id in self._execution_order:
            adapter = self._adapters.get(node_id)
            if adapter is None:
                continue
            inputs: dict[str, DataEnvelope] = {}
            for edge in self._graph.get_edges_to(node_id):
                src_outputs = outputs.get(edge.source_node_id, {})
                if edge.source_port in src_outputs:
                    inputs[edge.target_port] = src_outputs[edge.source_port]
            adapter.prepare_tick(self._tick_counter, self._variables)
            result = adapter.execute(inputs)
            outputs[node_id] = result or {}
            self._record_probe_outputs(node_id, outputs[node_id])

        return outputs

    def _record_probe_outputs(self, node_id: str, outputs: dict[str, DataEnvelope]) -> None:
        if not outputs:
            return

        port_map = self._probe_history.setdefault(node_id, {})
        for port_name, envelope in outputs.items():
            history = port_map.setdefault(port_name, deque(maxlen=self._probe_history_limit))
            history.appendleft(
                {
                    "port_name": port_name,
                    "data_type": envelope.data_type,
                    "timestamp": float(envelope.timestamp),
                    "center_freq": float(envelope.center_freq),
                    "sample_rate": float(envelope.sample_rate),
                    "payload_summary": self._describe_payload(envelope.payload),
                    "metadata_summary": self._summarize_metadata(envelope.metadata),
                }
            )

    @staticmethod
    def _describe_payload(payload: Any) -> str:
        if hasattr(payload, "shape") and hasattr(payload, "dtype"):
            shape = "x".join(str(part) for part in getattr(payload, "shape", ()))
            return f"{shape or 'scalar'} / {payload.dtype}"
        if isinstance(payload, dict):
            return f"dict ({len(payload)} alan)"
        if isinstance(payload, (list, tuple, set)):
            return f"{type(payload).__name__} ({len(payload)})"
        return type(payload).__name__

    @staticmethod
    def _summarize_metadata(metadata: dict[str, Any]) -> str:
        if not metadata:
            return "-"

        important_keys = [
            "fft_size",
            "active_tracks",
            "confirmed_count",
            "target_count",
            "waterfall_row",
        ]
        parts: list[str] = []
        for key in important_keys:
            if key not in metadata:
                continue
            value = metadata[key]
            if hasattr(value, "shape"):
                parts.append(f"{key}={getattr(value, 'shape', ())}")
            else:
                parts.append(f"{key}={value}")

        if parts:
            return ", ".join(parts[:4])
        return ", ".join(list(metadata.keys())[:4])


