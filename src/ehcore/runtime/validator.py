"""
Pipeline Validator — Çalıştırma öncesi doğrulama kuralları.

Kontroller:
1. Zorunlu config eksik
2. Zorunlu giriş bağlı değil
3. Port tipi uyumsuz
4. Cycle oluşumu
5. Kaynak node yok
6. Sink/görüntüleyici yoksa uyarı
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from ehcore.contracts import check_port_compatibility
from ehcore.registry import NodeRegistry

from .graph import PipelineGraph
from .scheduler import CycleDetectedError, topological_sort


class Severity(Enum):
    ERROR = auto()
    WARNING = auto()


@dataclass
class ValidationMessage:
    """Tek bir doğrulama mesajı."""
    severity: Severity
    node_id: str           # İlgili node instance ID (boş olabilir)
    message: str           # Türkçe açıklama


class ValidationError(Exception):
    """Pipeline doğrulama hataları."""
    def __init__(self, messages: list[ValidationMessage]) -> None:
        self.messages = messages
        errors = [m for m in messages if m.severity == Severity.ERROR]
        super().__init__(
            f"{len(errors)} doğrulama hatası bulundu. "
            + "; ".join(m.message for m in errors[:3])
        )


def _check_basic_topology(graph: PipelineGraph, messages: list[ValidationMessage]) -> bool:
    if len(graph) == 0:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            node_id="",
            message="Pipeline boş — en az bir node ekleyin.",
        ))
        return False

    sources = graph.get_source_nodes()
    if not sources:
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            node_id="",
            message="Pipeline'da kaynak (source) node bulunamadı.",
        ))

    sinks = graph.get_sink_nodes()
    if not sinks:
        messages.append(ValidationMessage(
            severity=Severity.WARNING,
            node_id="",
            message="Pipeline'da görüntüleyici (sink) node yok — çıktı görünmeyecek.",
        ))
    return True


def _check_cycles(graph: PipelineGraph, messages: list[ValidationMessage]) -> bool:
    try:
        topological_sort(graph)
    except CycleDetectedError as e:
        node_ids = e.args[0]
        names = []
        for nid in node_ids:
            node = graph.get_node(nid)
            if node:
                adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
                display_name = adapter_cls.descriptor.display_name if adapter_cls else node.node_type_id
                names.append(f"[{display_name}]")
            else:
                names.append(f"[{nid}]")
        
        messages.append(ValidationMessage(
            severity=Severity.ERROR,
            node_id="",
            message=f"Sistem üzerinde döngü tespit edildi. Döngüye dahil bloklar: {', '.join(names)}",
        ))
        return False
    return True


def _check_node_requirements(graph: PipelineGraph, messages: list[ValidationMessage]) -> None:
    for node in graph.nodes:
        adapter_cls = NodeRegistry.get_adapter_class(node.node_type_id)
        if adapter_cls is None:
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                node_id=node.instance_id,
                message=f"Bilinmeyen node tipi: '{node.node_type_id}'",
            ))
            continue

        descriptor = adapter_cls.descriptor

        # Zorunlu config kontrolü
        config_errors = descriptor.validate_config(node.config)
        for err in config_errors:
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                node_id=node.instance_id,
                message=f"[{descriptor.display_name}] {err}",
            ))

        # Zorunlu input port bağlantı kontrolü
        connected_input_ports = {
            e.target_port
            for e in graph.get_edges_to(node.instance_id)
        }
        for port in descriptor.input_ports:
            if port.required and port.name not in connected_input_ports:
                messages.append(ValidationMessage(
                    severity=Severity.ERROR,
                    node_id=node.instance_id,
                    message=(
                        f"[{descriptor.display_name}] "
                        f"Zorunlu giriş '{port.display_name}' bağlı değil."
                    ),
                ))


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
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                node_id=edge.source_node_id,
                message=f"Geçersiz port adı: {edge.source_port} → {edge.target_port}",
            ))
            continue

        if not check_port_compatibility(src_port.port_type, tgt_port.port_type):
            messages.append(ValidationMessage(
                severity=Severity.ERROR,
                node_id=edge.source_node_id,
                message=(
                    f"Port tipi uyumsuz: "
                    f"{src_port.display_name} ({src_port.port_type.name}) → "
                    f"{tgt_port.display_name} ({tgt_port.port_type.name})"
                ),
            ))


def validate_pipeline(graph: PipelineGraph) -> list[ValidationMessage]:
    """
    Pipeline'ı doğrula ve mesajları döndür.

    Returns:
        Doğrulama mesajları listesi (ERROR ve WARNING).

    Raises:
        ValidationError: Kritik hatalar varsa (caller'ın tercihi).
    """
    messages: list[ValidationMessage] = []

    if not _check_basic_topology(graph, messages):
        return messages

    if not _check_cycles(graph, messages):
        return messages

    _check_node_requirements(graph, messages)
    _check_port_compatibility(graph, messages)

    return messages
