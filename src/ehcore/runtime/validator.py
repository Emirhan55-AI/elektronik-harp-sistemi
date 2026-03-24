"""
Pipeline dogrulama kurallari.

Iki farkli baglam desteklenir:
- edit: yapisal geri bildirim
- run: calistirmayi engelleyen kritik kontroller
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from ehcore.contracts import check_port_compatibility
from ehcore.registry import NodeRegistry

from .graph import PipelineGraph
from .scheduler import CycleDetectedError, topological_sort
from .variables import validate_variable_usage


class Severity(Enum):
    ERROR = auto()
    WARNING = auto()


class ValidationPhase(Enum):
    EDIT = "edit"
    RUN = "run"


@dataclass
class ValidationMessage:
    severity: Severity
    node_id: str
    message: str


class ValidationError(Exception):
    """Pipeline dogrulama hatalari."""

    def __init__(self, messages: list[ValidationMessage]) -> None:
        self.messages = messages
        errors = [message for message in messages if message.severity == Severity.ERROR]
        super().__init__(
            f"{len(errors)} dogrulama hatasi bulundu. "
            + "; ".join(message.message for message in errors[:3])
        )


def validate_pipeline(
    graph: PipelineGraph,
    phase: ValidationPhase | str = ValidationPhase.RUN,
) -> list[ValidationMessage]:
    actual_phase = ValidationPhase(phase)
    messages: list[ValidationMessage] = []

    if not _check_basic_topology(graph, messages, actual_phase):
        return messages
    if not _check_cycles(graph, messages):
        return messages

    _check_node_requirements(graph, messages, actual_phase)
    _check_port_compatibility(graph, messages)
    _check_unused_outputs(graph, messages, actual_phase)
    return messages


def validate_edit_pipeline(graph: PipelineGraph) -> list[ValidationMessage]:
    return validate_pipeline(graph, phase=ValidationPhase.EDIT)


def validate_run_pipeline(graph: PipelineGraph) -> list[ValidationMessage]:
    return validate_pipeline(graph, phase=ValidationPhase.RUN)


def _check_basic_topology(
    graph: PipelineGraph,
    messages: list[ValidationMessage],
    phase: ValidationPhase,
) -> bool:
    if len(graph) == 0:
        messages.append(
            ValidationMessage(
                severity=Severity.ERROR,
                node_id="",
                message="Pipeline boş - en az bir blok ekleyin.",
            )
        )
        return False

    sources = graph.get_source_nodes()
    if not sources:
        messages.append(
            ValidationMessage(
                severity=Severity.ERROR,
                node_id="",
                message="Pipeline'da kaynak blok bulunamadı.",
            )
        )

    sinks = graph.get_sink_nodes()
    if not sinks:
        severity = Severity.WARNING if phase == ValidationPhase.RUN else Severity.WARNING
        messages.append(
            ValidationMessage(
                severity=severity,
                node_id="",
                message="Pipeline'da görüntüleyici blok yok - çıktı izlenemeyecek.",
            )
        )
    return True


def _check_cycles(graph: PipelineGraph, messages: list[ValidationMessage]) -> bool:
    try:
        topological_sort(graph)
    except CycleDetectedError as exc:
        node_ids = exc.args[0]
        names: list[str] = []
        for node_id in node_ids:
            node = graph.get_node(node_id)
            if node is None:
                names.append(f"[{node_id}]")
                continue
            adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
            display_name = adapter_cls.descriptor.display_name if adapter_cls else node.node_type_id
            names.append(f"[{display_name}]")
        messages.append(
            ValidationMessage(
                severity=Severity.ERROR,
                node_id="",
                message=f"Sistem üzerinde döngü tespit edildi. Dahil bloklar: {', '.join(names)}",
            )
        )
        return False
    return True


def _check_node_requirements(
    graph: PipelineGraph,
    messages: list[ValidationMessage],
    phase: ValidationPhase,
) -> None:
    variables = graph.variables
    for node in graph.nodes:
        adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
        if adapter_cls is None:
            messages.append(
                ValidationMessage(
                    severity=Severity.ERROR,
                    node_id=node.instance_id,
                    message=f"Bilinmeyen blok tipi: '{node.node_type_id}'",
                )
            )
            continue

        descriptor = adapter_cls.descriptor

        if phase == ValidationPhase.RUN:
            for err in descriptor.validate_config(node.config):
                messages.append(
                    ValidationMessage(
                        severity=Severity.ERROR,
                        node_id=node.instance_id,
                        message=f"[{descriptor.display_name}] {err}",
                    )
                )

        for err in validate_variable_usage(node.config, variables):
            severity = Severity.ERROR if phase == ValidationPhase.RUN else Severity.WARNING
            messages.append(
                ValidationMessage(
                    severity=severity,
                    node_id=node.instance_id,
                    message=f"[{descriptor.display_name}] Değişken hatası: {err}",
                )
            )

        connected_input_ports = {edge.target_port for edge in graph.get_edges_to(node.instance_id)}
        for port in descriptor.input_ports:
            if port.required and port.name not in connected_input_ports:
                severity = Severity.ERROR if phase == ValidationPhase.RUN else Severity.WARNING
                messages.append(
                    ValidationMessage(
                        severity=severity,
                        node_id=node.instance_id,
                        message=f"[{descriptor.display_name}] Zorunlu giriş '{port.display_name}' bağlı değil.",
                    )
                )


def _check_port_compatibility(graph: PipelineGraph, messages: list[ValidationMessage]) -> None:
    for edge in graph.edges:
        source_node = graph.get_node(edge.source_node_id)
        target_node = graph.get_node(edge.target_node_id)
        if source_node is None or target_node is None:
            continue

        src_cls = NodeRegistry.get_adapter_class(source_node.node_type_id)
        tgt_cls = NodeRegistry.get_adapter_class(target_node.node_type_id)
        if src_cls is None or tgt_cls is None:
            continue

        src_port = src_cls.descriptor.get_output_port(edge.source_port)
        tgt_port = tgt_cls.descriptor.get_input_port(edge.target_port)

        if src_port is None or tgt_port is None:
            messages.append(
                ValidationMessage(
                    severity=Severity.ERROR,
                    node_id=edge.source_node_id,
                    message=f"Geçersiz port adı: {edge.source_port} -> {edge.target_port}",
                )
            )
            continue

        if not check_port_compatibility(src_port.port_type, tgt_port.port_type):
            messages.append(
                ValidationMessage(
                    severity=Severity.ERROR,
                    node_id=edge.source_node_id,
                    message=(
                        f"Port tipi uyumsuz: "
                        f"{src_port.display_name} ({src_port.port_type.name}) -> "
                        f"{tgt_port.display_name} ({tgt_port.port_type.name})"
                    ),
                )
            )


def _check_unused_outputs(
    graph: PipelineGraph,
    messages: list[ValidationMessage],
    phase: ValidationPhase,
) -> None:
    if phase != ValidationPhase.RUN:
        return

    for node in graph.nodes:
        adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
        if adapter_cls is None:
            continue
        descriptor = adapter_cls.descriptor
        connected_output_ports = {edge.source_port for edge in graph.get_edges_from(node.instance_id)}
        for port in descriptor.output_ports:
            if not port.visible or port.name in connected_output_ports:
                continue
            messages.append(
                ValidationMessage(
                    severity=Severity.WARNING,
                    node_id=node.instance_id,
                    message=f"[{descriptor.display_name}] Çıkış '{port.display_name}' boşta - kullanılmıyor.",
                )
            )
