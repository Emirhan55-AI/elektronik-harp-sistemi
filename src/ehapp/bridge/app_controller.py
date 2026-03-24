"""
AppController - runtime yasam dongusu ve UI koordinasyonu.

Tek merkezi kontrol noktasi:
- Pipeline graph yonetimi
- Engine start/stop/reset
- Canvas <-> runtime senkronizasyonu
- Grafik guncelleme
"""

from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ehapp.strings import tr
from ehcore.contracts import NodeDescriptor
from ehcore.registry import NodeRegistry
from ehcore.runtime import (
    PipelineEngine,
    PipelineGraph,
    RuntimeIssue,
    validate_edit_pipeline,
    validate_run_pipeline,
)
from ehcore.runtime.validator import Severity

from .workers import PipelineWorker, PlotRefreshTimer


class AppController(QObject):
    """Uygulama merkezi kontrol birimi."""

    pipeline_started = Signal()
    pipeline_stopped = Signal()
    pipeline_error = Signal(str)
    log_message = Signal(str, str)
    issues_changed = Signal()
    variables_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._graph = PipelineGraph()
        self._engine: PipelineEngine | None = None

        self._worker = PipelineWorker(self)
        self._worker.state_changed.connect(self._on_state_change)
        self._worker.error_occurred.connect(self._on_engine_error)
        self._worker.log_message.connect(self._forward_worker_log)

        self._plot_timer = PlotRefreshTimer(interval_ms=50, parent=self)
        self._plot_timer.confirmed_targets_ready.connect(self._log_new_targets)

        self._known_target_ids: set[int] = set()
        self._runtime_issues: list[RuntimeIssue] = []
        self._preview_issues: list[RuntimeIssue] = []

    @property
    def graph(self) -> PipelineGraph:
        return self._graph

    @property
    def engine(self) -> PipelineEngine | None:
        return self._engine

    @property
    def plot_timer(self) -> PlotRefreshTimer:
        return self._plot_timer

    @property
    def issues(self) -> list[RuntimeIssue]:
        return self._merge_issues()

    @property
    def variables(self) -> dict[str, object]:
        return self._graph.variables

    def set_graph(self, graph: PipelineGraph, announce: bool = True) -> None:
        """Grafiği dışarıdan yükle."""
        self.stop_pipeline()
        self._graph = graph
        self._known_target_ids.clear()
        self.clear_issues()
        self.variables_changed.emit()
        if announce:
            self.log_message.emit(tr.LOG_GRAPH_LOADED, "info")

    def refresh_preview_issues(self) -> list[RuntimeIssue]:
        if self._engine is not None or len(self._graph) == 0:
            self.clear_preview_issues()
            return []

        preview_issues = [
            RuntimeIssue(
                severity="error" if message.severity == Severity.ERROR else "warning",
                message=message.message,
                node_id=message.node_id,
                source="preview",
                timestamp=0.0,
            )
            for message in validate_edit_pipeline(self._graph)
        ]
        if preview_issues == self._preview_issues:
            return list(self._preview_issues)

        self._preview_issues = preview_issues
        self.issues_changed.emit()
        return list(self._preview_issues)

    def clear_preview_issues(self) -> None:
        if not self._preview_issues:
            return
        self._preview_issues.clear()
        self.issues_changed.emit()

    def _log_new_targets(self, conf_array, cf, sr, fft_size: int = 0) -> None:
        del fft_size
        if conf_array.size == 0:
            return

        for row in conf_array:
            target_id = int(row["target_id"])
            if target_id in self._known_target_ids:
                continue

            freq_hz = row["center_freq_normalized"] * sr + cf
            freq_mhz = freq_hz / 1e6
            power = row["power_db"]
            snr = row["snr_db"]
            message = tr.LOG_TARGET_CONFIRMED.format(
                target_id=target_id,
                freq_mhz=freq_mhz,
                power=power,
                snr=snr,
            )
            self.log_message.emit(message, "success")
            self._known_target_ids.add(target_id)

    def add_node(
        self,
        node_type_id: str,
        position: tuple[float, float] = (0.0, 0.0),
        config: dict | None = None,
    ) -> str | None:
        if self._engine is not None:
            self.stop_pipeline()

        descriptor = self._get_descriptor(node_type_id)
        if descriptor is None:
            self.log_message.emit(
                tr.LOG_UNKNOWN_NODE_TYPE.format(node_type_id=node_type_id),
                "error",
            )
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
        self.clear_issues()
        self.log_message.emit(
            tr.LOG_NODE_ADDED.format(name=descriptor.display_name),
            "info",
        )
        return instance_id

    def remove_node(self, instance_id: str) -> None:
        if self._engine is not None:
            self.stop_pipeline()
        self._graph.remove_node(instance_id)
        self.clear_issues()

    def update_node_config(self, instance_id: str, config: dict) -> None:
        node = self._graph.get_node(instance_id)
        if node is None:
            return

        node.config.update(config)
        if self._engine is not None:
            self._engine.update_node_config(instance_id, config)
        self.clear_issues()
        self.log_message.emit(tr.LOG_NODE_CONFIG_UPDATED, "info")

    def update_node_position(self, instance_id: str, x: float, y: float) -> None:
        node = self._graph.get_node(instance_id)
        if node is not None:
            node.position = (x, y)

    def set_variables(self, variables: dict[str, object]) -> list[str]:
        self._graph.set_variables(variables)
        self.variables_changed.emit()
        self.clear_issues()

        if self._engine is None:
            self.log_message.emit(tr.LOG_VARIABLES_UPDATED, "info")
            return []

        errors = self._engine.update_variables(variables)
        if errors:
            for error in errors:
                self.log_message.emit(error, "error")
                self._append_runtime_issue(
                    RuntimeIssue(
                        severity="error",
                        message=error,
                        source="runtime",
                    )
                )
            return errors

        self.log_message.emit(tr.LOG_VARIABLES_UPDATED, "info")
        return []

    def add_edge(
        self,
        src_node: str,
        src_port: str,
        tgt_node: str,
        tgt_port: str,
    ) -> bool:
        if self._engine is not None:
            self.stop_pipeline()
        try:
            self._graph.add_edge(src_node, src_port, tgt_node, tgt_port)
            self.clear_issues()
            return True
        except ValueError as exc:
            self.log_message.emit(str(exc), "warning")
            return False

    def remove_edge(
        self,
        src_node: str,
        src_port: str,
        tgt_node: str,
        tgt_port: str,
    ) -> bool:
        if self._engine is not None:
            self.stop_pipeline()
        removed = self._graph.remove_edge_between(src_node, src_port, tgt_node, tgt_port)
        if removed:
            self.clear_issues()
        return removed

    def start_pipeline(self) -> list[str]:
        """Pipeline'i baslat. Hata mesaji listesi doner."""
        if self._engine is not None:
            self.stop_pipeline()

        self.clear_preview_issues()
        messages = validate_run_pipeline(self._graph)
        errors = [message for message in messages if message.severity == Severity.ERROR]
        warnings = [message for message in messages if message.severity == Severity.WARNING]
        self._set_runtime_issues(
            [
                RuntimeIssue(
                    severity="error" if message.severity == Severity.ERROR else "warning",
                    message=message.message,
                    node_id=message.node_id,
                    source="validation",
                )
                for message in messages
            ]
        )

        for warning in warnings:
            self.log_message.emit(warning.message, "warning")

        if errors:
            for error in errors:
                self.log_message.emit(error.message, "error")
            return [error.message for error in errors]

        self._engine = PipelineEngine(
            self._graph,
            on_error=self._worker.on_error,
            on_state_change=self._worker.on_state_change,
        )

        start_errors = self._engine.start()
        if start_errors:
            for error in start_errors:
                self.log_message.emit(error, "error")
            self._append_runtime_issue(
                RuntimeIssue(
                    severity="error",
                    message="\n".join(start_errors),
                    source="runtime",
                )
            )
            self._engine = None
            return start_errors

        self._plot_timer.set_engine(self._engine)
        self._plot_timer.start()
        self.pipeline_started.emit()
        self.log_message.emit(tr.LOG_PIPELINE_STARTED, "success")
        return []

    def stop_pipeline(self) -> None:
        was_running = self._engine is not None
        self._plot_timer.stop()
        self._plot_timer.set_engine(None)
        if self._engine is not None:
            self._engine.stop()
            self._engine = None
        self._known_target_ids.clear()
        if not was_running:
            return
        self.pipeline_stopped.emit()
        self.log_message.emit(tr.LOG_PIPELINE_STOPPED, "info")

    def reset_all(self) -> None:
        self.stop_pipeline()
        self._graph = PipelineGraph()
        self.clear_issues()
        self.variables_changed.emit()
        self.log_message.emit(tr.LOG_WORKSPACE_RESET, "info")

    def clear_issues(self) -> None:
        if not self._runtime_issues and not self._preview_issues:
            return
        self._runtime_issues.clear()
        self._preview_issues.clear()
        self.issues_changed.emit()

    def get_node_runtime_info(self, instance_id: str) -> dict:
        node = self._graph.get_node(instance_id)
        if node is None:
            return {}

        descriptor = self._get_descriptor(node.node_type_id)
        adapter = self._engine.adapters.get(instance_id) if self._engine is not None else None
        metrics = adapter.metrics_snapshot() if adapter is not None else None
        manifest = NodeRegistry.get_manifest(node.node_type_id)
        probe_snapshot: list[dict] = []
        probe_history: list[dict] = []
        if self._engine is not None:
            probe_history = self._engine.get_probe_history(instance_id, limit=8)
            probe_snapshot = probe_history[:3]

        return {
            "instance_id": instance_id,
            "node_type_id": node.node_type_id,
            "display_name": descriptor.display_name if descriptor else node.node_type_id,
            "description": descriptor.description if descriptor else "",
            "state": adapter.state if adapter is not None else "idle",
            "last_error": adapter.error_message if adapter is not None else "",
            "metrics": metrics,
            "input_ports": descriptor.input_ports if descriptor else (),
            "output_ports": descriptor.output_ports if descriptor else (),
            "manifest": manifest,
            "probe_snapshot": probe_snapshot,
            "probe_history": probe_history,
        }

    def get_runtime_overview(self) -> dict[str, object]:
        issues = self.issues
        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity != "error")
        preview_count = sum(1 for issue in issues if issue.source == "preview")
        runtime_count = len(issues) - preview_count

        node_count = len(self._graph.nodes)
        variable_count = len(self._graph.variables)
        active_node_count = 0
        avg_latency_ms = 0.0
        slowest_node_label = tr.COMMON_PLACEHOLDER

        if self._engine is not None:
            metrics_by_node: list[tuple[str, object]] = []
            for node_id, adapter in self._engine.adapters.items():
                if adapter.state == "running":
                    active_node_count += 1
                metrics = adapter.metrics_snapshot()
                if metrics.frame_count > 0:
                    metrics_by_node.append((node_id, metrics))

            if metrics_by_node:
                avg_latency_ms = sum(
                    metrics.average_process_duration_ms
                    for _, metrics in metrics_by_node
                ) / len(metrics_by_node)
                slowest_node_id, slowest_metrics = max(
                    metrics_by_node,
                    key=lambda item: item[1].last_process_duration_ms,
                )
                node = self._graph.get_node(slowest_node_id)
                descriptor = self._get_descriptor(node.node_type_id) if node is not None else None
                slowest_name = descriptor.display_name if descriptor is not None else slowest_node_id
                slowest_node_label = (
                    f"{slowest_name} ({slowest_metrics.last_process_duration_ms:.1f} ms)"
                )

        return {
            "issue_count": len(issues),
            "error_count": error_count,
            "warning_count": warning_count,
            "preview_issue_count": preview_count,
            "runtime_issue_count": runtime_count,
            "node_count": node_count,
            "active_node_count": active_node_count,
            "variable_count": variable_count,
            "avg_latency_ms": avg_latency_ms,
            "slowest_node_label": slowest_node_label,
            "source_label": self._summarize_source(),
        }

    def _get_descriptor(self, node_type_id: str) -> NodeDescriptor | None:
        adapter_cls = NodeRegistry.get_adapter_class(node_type_id)
        if adapter_cls:
            return adapter_cls.descriptor
        return None

    def _forward_worker_log(self, message: str, level: str) -> None:
        self.log_message.emit(message, level)

    def _on_state_change(self, state: str) -> None:
        if state == "error":
            self.stop_pipeline()
            self.pipeline_error.emit(tr.ERROR_SYSTEM_RUNTIME)

    def _on_engine_error(self, node_id: str, msg: str) -> None:
        self._append_runtime_issue(
            RuntimeIssue(
                severity="error",
                message=msg,
                node_id=node_id,
                source="runtime",
            )
        )
        self.pipeline_error.emit(msg)

    def _set_runtime_issues(self, issues: list[RuntimeIssue]) -> None:
        self._runtime_issues = issues
        self.issues_changed.emit()

    def _append_runtime_issue(self, issue: RuntimeIssue) -> None:
        self._runtime_issues.append(issue)
        self.issues_changed.emit()

    def _merge_issues(self) -> list[RuntimeIssue]:
        merged: list[RuntimeIssue] = []
        seen: set[tuple[str, str, str, str, str]] = set()
        for issue in [*self._runtime_issues, *self._preview_issues]:
            key = (
                issue.severity,
                issue.message,
                issue.node_id,
                issue.source,
                issue.code,
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(issue)
        return merged

    def _summarize_source(self) -> str:
        for node in self._graph.nodes:
            if node.node_type_id != "sigmf_source":
                continue
            file_path = str(node.config.get("file_path", "")).strip()
            if not file_path:
                return tr.SUMMARY_SOURCE_NOT_SELECTED
            source_name = Path(file_path).name or file_path
            loop_enabled = bool(node.config.get("loop", False))
            mode_label = tr.SUMMARY_SOURCE_LOOP if loop_enabled else tr.SUMMARY_SOURCE_SINGLE_PASS
            return tr.SUMMARY_SOURCE_LABEL.format(name=source_name, mode=mode_label)
        return tr.COMMON_PLACEHOLDER
