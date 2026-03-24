"""
PipelineEngine — Headless pipeline yürütme motoru.

Topological sort sırasına göre node'ları yürütür.
Her node'un process() çağrılır, çıktı sonraki node'a aktarılır.
Node bazında hata yakalama — hatalı node atlanır, pipeline durmaz.

Bu modül PySide6'dan bağımsızdır; worker thread'den çağrılmalıdır.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from ehcore.adapters._base import BaseAdapter
from ehcore.contracts import DataEnvelope
from ehcore.registry import NodeRegistry

from .graph import PipelineGraph, Edge
from .scheduler import topological_sort
from .validator import validate_pipeline, Severity

logger = logging.getLogger(__name__)


class PipelineEngine:
    """
    Headless pipeline yürütme motoru.

    Kullanım:
        engine = PipelineEngine(graph)
        engine.start()    # Arka plan thread'inde çalışır
        engine.stop()
    """

    def __init__(
        self,
        graph: PipelineGraph,
        on_error: Callable[[str, str], None] | None = None,
        on_state_change: Callable[[str], None] | None = None,
        tick_interval: float = 0.05,  # 50ms → ~20 FPS
    ) -> None:
        self._graph = graph
        self._on_error = on_error         # (node_id, error_msg)
        self._on_state_change = on_state_change  # ("idle" | "running" | "error")
        self._tick_interval = tick_interval

        self._adapters: dict[str, BaseAdapter] = {}
        self._execution_order: list[str] = []
        self._state: str = "idle"

        # Arka plan execution
        self._thread: threading.Thread | None = None
        self._running = threading.Event()

        # Son iterasyonun çıktılarını tutar (UI güncellemesi için)
        self.last_outputs: dict[str, dict[str, DataEnvelope]] = {}

    # ── Yaşam Döngüsü ───────────────────────────────────────────

    def start(self) -> list[str]:
        """
        Pipeline'ı doğrula, adapter'ları oluştur ve çalıştır.

        Returns:
            Hata mesajları listesi (boş = başarılı başlangıç).
        """
        # Doğrulama
        messages = validate_pipeline(self._graph)
        errors = [m for m in messages if m.severity == Severity.ERROR]
        if errors:
            return [m.message for m in errors]

        # Execution order
        self._execution_order = topological_sort(self._graph)

        # Adapter instance'ları oluştur ve configure et
        self._adapters.clear()
        for node_id in self._execution_order:
            node = self._graph.get_node(node_id)
            if node is None:
                continue

            adapter = NodeRegistry.create_instance(node.node_type_id)
            if adapter is None:
                return [f"Adapter oluşturulamadı: {node.node_type_id}"]

            try:
                adapter.configure(node.config)
                adapter.start()
            except Exception as e:
                return [f"Adapter yapılandırma hatası ({node.node_type_id}): {e}"]

            self._adapters[node_id] = adapter

        # Thread başlat
        self._running.set()
        self._set_state("running")
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="pipeline-engine",
        )
        self._thread.start()
        logger.info("Pipeline başlatıldı (%d node).", len(self._execution_order))
        return []

    def stop(self) -> None:
        """Pipeline'ı durdur."""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        
        self.last_outputs = {} # Eski verileri temizle

        # Adapter'ları durdur
        for adapter in self._adapters.values():
            try:
                adapter.stop()
            except Exception:
                pass

        self._set_state("idle")
        logger.info("Pipeline durduruldu.")

    def reset(self) -> None:
        """Durdur ve sıfırla."""
        self.stop()
        for adapter in self._adapters.values():
            try:
                adapter.reset()
            except Exception:
                pass
        self._adapters.clear()
        self._execution_order.clear()

    @property
    def state(self) -> str:
        return self._state

    @property
    def adapters(self) -> dict[str, BaseAdapter]:
        """Çalışan adapter instance'ları (bridge tarafından okunur)."""
        return self._adapters

    # ── Çalışma Döngüsü ─────────────────────────────────────────

    def _run_loop(self) -> None:
        """Ana yürütme döngüsü (worker thread)."""
        while self._running.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("Pipeline tick hatası")
                self._set_state("error")
                self._running.clear()
                return

            time.sleep(self._tick_interval)

    def _tick(self) -> None:
        """Tek yürütme adımı — tüm node'ları sırayla çalıştır."""
        # Her node'un çıktısını tut
        outputs: dict[str, dict[str, DataEnvelope]] = {}

        for node_id in self._execution_order:
            adapter = self._adapters.get(node_id)
            if adapter is None:
                continue

            if adapter.state == "error":
                continue  # Hatalı node'u atla

            # Bu node'un giriş verisini topla
            inputs: dict[str, DataEnvelope] = {}
            for edge in self._graph.get_edges_to(node_id):
                src_outputs = outputs.get(edge.source_node_id, {})
                if edge.source_port in src_outputs:
                    inputs[edge.target_port] = src_outputs[edge.source_port]

            # Process çağır
            try:
                result = adapter.process(inputs)
                outputs[node_id] = result or {}
            except Exception as e:
                error_msg = f"[{node_id}] İşleme hatası: {e}"
                logger.error(error_msg)
                adapter.set_error(str(e))
                if self._on_error:
                    self._on_error(node_id, error_msg)

        # UI'nin çekebilmesi için son çıktıyı kaydet
        # Thread-safe copy for UI access
        self.last_outputs = copy.copy(outputs)

    def _set_state(self, new_state: str) -> None:
        """State değişikliğini bildir."""
        self._state = new_state
        if self._on_state_change:
            self._on_state_change(new_state)

    def update_node_config(self, instance_id: str, new_config: dict) -> None:
        """Çalışmakta olan bir adapter'ın ayarlarını güncelle (properties panel)."""
        adapter = self._adapters.get(instance_id)
        if adapter is not None:
            adapter.configure(new_config)

    # ── Tek adım çalıştırma (test amaçlı) ───────────────────────

    def single_tick(self) -> dict[str, dict[str, DataEnvelope]]:
        """
        Tek bir tick çalıştır ve çıktıları döndür (test/debug için).
        Pipeline'ın start() ile başlatılmış olması gerekmez.
        """
        if not self._adapters:
            # Adapter'ları yarat
            self._execution_order = topological_sort(self._graph)
            for node_id in self._execution_order:
                node = self._graph.get_node(node_id)
                if node is None:
                    continue
                adapter = NodeRegistry.create_instance(node.node_type_id)
                if adapter is not None:
                    adapter.configure(node.config)
                    self._adapters[node_id] = adapter

        outputs: dict[str, dict[str, DataEnvelope]] = {}
        for node_id in self._execution_order:
            adapter = self._adapters.get(node_id)
            if adapter is None:
                continue
            inputs: dict[str, DataEnvelope] = {}
            for edge in self._graph.get_edges_to(node_id):
                src_outputs = outputs.get(edge.source_node_id, {})
                if edge.source_port in src_outputs:
                    inputs[edge.target_port] = src_outputs[edge.source_port]
            result = adapter.process(inputs)
            outputs[node_id] = result or {}

        return outputs
