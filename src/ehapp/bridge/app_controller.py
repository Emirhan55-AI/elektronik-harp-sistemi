"""
AppController — Runtime yaşam döngüsü ve UI koordinasyonu.

Tek merkezi kontrol noktası:
- Pipeline graph yönetimi
- Engine start/stop/reset
- Canvas ↔ Runtime senkronizasyonu
- Grafik güncelleme
"""

from __future__ import annotations

import uuid
from PySide6.QtCore import QObject, Signal, QPointF

from ehcore.runtime import PipelineGraph, PipelineEngine, validate_pipeline
from ehcore.runtime.validator import Severity
from ehcore.registry import NodeRegistry
from ehcore.contracts import NodeDescriptor

from .workers import PipelineWorker, PlotRefreshTimer


class AppController(QObject):
    """Uygulama merkezi kontrol birimi."""

    # Sinyaller
    pipeline_started = Signal()
    pipeline_stopped = Signal()
    pipeline_error = Signal(str)
    log_message = Signal(str, str)  # (message, level)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._graph = PipelineGraph()
        self._engine: PipelineEngine | None = None

        # Worker
        self._worker = PipelineWorker(self)
        self._worker.state_changed.connect(self._on_state_change)
        self._worker.error_occurred.connect(self._on_engine_error)

        # Plot refresh
        self._plot_timer = PlotRefreshTimer(interval_ms=50, parent=self)

    @property
    def graph(self) -> PipelineGraph:
        return self._graph

    @property
    def engine(self) -> PipelineEngine | None:
        return self._engine

    @property
    def plot_timer(self) -> PlotRefreshTimer:
        return self._plot_timer

    def set_graph(self, graph: PipelineGraph) -> None:
        """Grafiği dışarıdan yükle (Persistence için)."""
        self.stop_pipeline()
        self._graph = graph
        self.log_message.emit("Yeni proje yüklendi.", "info")

    # ── Node yönetimi ────────────────────────────────────────────

    def add_node(
        self,
        node_type_id: str,
        position: tuple[float, float] = (0.0, 0.0),
        config: dict | None = None,
    ) -> str | None:
        """Node ekle. Instance ID döner."""
        descriptor = self._get_descriptor(node_type_id)
        if descriptor is None:
            self.log_message.emit(f"Bilinmeyen node tipi: {node_type_id}", "error")
            return None

        instance_id = uuid.uuid4().hex[:12]
        actual_config = descriptor.default_config()
        if config:
            actual_config.update(config)

        self._graph.add_node(
            node_type_id=node_type_id,
            config=actual_config,
            position=position,
            instance_id=instance_id,
        )
        self.log_message.emit(f"Node eklendi: {descriptor.display_name}", "info")
        return instance_id

    def remove_node(self, instance_id: str) -> None:
        self._graph.remove_node(instance_id)

    def update_node_config(self, instance_id: str, config: dict) -> None:
        node = self._graph.get_node(instance_id)
        if node:
            node.config.update(config)
            if self._engine is not None:
                self._engine.update_node_config(instance_id, config)
            self.log_message.emit("Node ayarları güncellendi.", "info")

    def update_node_position(self, instance_id: str, x: float, y: float) -> None:
        node = self._graph.get_node(instance_id)
        if node:
            node.position = (x, y)

    # ── Edge yönetimi ────────────────────────────────────────────

    def add_edge(
        self,
        src_node: str, src_port: str,
        tgt_node: str, tgt_port: str,
    ) -> bool:
        try:
            self._graph.add_edge(src_node, src_port, tgt_node, tgt_port)
            return True
        except ValueError as e:
            self.log_message.emit(str(e), "warning")
            return False

    # ── Pipeline kontrol ─────────────────────────────────────────

    def start_pipeline(self) -> list[str]:
        """Pipeline'ı başlat. Hata mesajları listesi döner."""
        if self._engine is not None:
            self.stop_pipeline()

        # Doğrulama
        messages = validate_pipeline(self._graph)
        errors = [m for m in messages if m.severity == Severity.ERROR]
        warnings = [m for m in messages if m.severity == Severity.WARNING]

        for w in warnings:
            self.log_message.emit(w.message, "warning")

        if errors:
            for e in errors:
                self.log_message.emit(e.message, "error")
            return [e.message for e in errors]

        # Engine oluştur ve başlat
        self._engine = PipelineEngine(
            self._graph,
            on_error=self._worker.on_error,
            on_state_change=self._worker.on_state_change,
        )

        start_errors = self._engine.start()
        if start_errors:
            for e in start_errors:
                self.log_message.emit(e, "error")
            self._engine = None
            return start_errors

        self._plot_timer.set_engine(self._engine)
        self._plot_timer.start()
        self.pipeline_started.emit()
        self.log_message.emit("Pipeline başlatıldı.", "success")
        return []

    def stop_pipeline(self) -> None:
        """Pipeline'ı durdur."""
        self._plot_timer.stop()
        if self._engine:
            self._engine.stop()
            self._engine = None
        self.pipeline_stopped.emit()
        self.log_message.emit("Pipeline durduruldu.", "info")

    def reset_all(self) -> None:
        """Tam sıfırlama."""
        self.stop_pipeline()
        self._graph = PipelineGraph()
        self.log_message.emit("Çalışma alanı sıfırlandı.", "info")

    # ── Yardımcılar ──────────────────────────────────────────────

    def _get_descriptor(self, node_type_id: str) -> NodeDescriptor | None:
        adapter_cls = NodeRegistry.get_adapter_class(node_type_id)
        if adapter_cls:
            return adapter_cls.descriptor
        return None

    def _on_state_change(self, state: str) -> None:
        if state == "error":
            self.stop_pipeline()
            self.pipeline_error.emit("Sistem hatası oluştu.")

    def _on_engine_error(self, node_id: str, msg: str) -> None:
        self.pipeline_error.emit(msg)
