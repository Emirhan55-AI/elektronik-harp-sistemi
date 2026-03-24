"""
Manifest tabanlı node katalog tipleri.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ehcore.contracts import NodeDescriptor, PortDef, PortType


@dataclass(frozen=True, slots=True)
class PortManifest:
    """UI ve runtime için ortak port tanımı."""

    name: str
    port_type: PortType
    display_name: str = ""
    required: bool = True
    visible: bool = True
    tooltip: str = ""

    def to_port_def(self) -> PortDef:
        return PortDef(
            name=self.name,
            port_type=self.port_type,
            display_name=self.display_name,
            required=self.required,
            visible=self.visible,
            tooltip=self.tooltip,
        )


@dataclass(frozen=True, slots=True)
class VisualizationBinding:
    """Bir output portunun hangi UI yüzeylerine bağlanacağını tarif eder."""

    port_name: str
    view_id: str
    metadata_key: str = ""


@dataclass(frozen=True, slots=True)
class NodeManifest:
    """Manifest tabanlı blok tanımı."""

    node_id: str
    display_name: str
    category: str
    description: str = ""
    algorithm_import_path: str = ""
    algorithm_class_name: str = ""
    input_ports: tuple[PortManifest, ...] = ()
    output_ports: tuple[PortManifest, ...] = ()
    config_schema: dict[str, Any] = field(default_factory=dict)
    ui_hints: dict[str, Any] = field(default_factory=dict)
    visualization_bindings: tuple[VisualizationBinding, ...] = ()
    debug_capabilities: tuple[str, ...] = ()
    compat_aliases: tuple[str, ...] = ()

    def to_descriptor(self) -> NodeDescriptor:
        return NodeDescriptor(
            node_id=self.node_id,
            display_name=self.display_name,
            category=self.category,
            description=self.description,
            input_ports=tuple(port.to_port_def() for port in self.input_ports),
            output_ports=tuple(port.to_port_def() for port in self.output_ports),
            config_schema=self.config_schema,
        )

    @classmethod
    def from_descriptor(cls, descriptor: NodeDescriptor) -> NodeManifest:
        return cls(
            node_id=descriptor.node_id,
            display_name=descriptor.display_name,
            category=descriptor.category,
            description=descriptor.description,
            input_ports=tuple(
                PortManifest(
                    name=port.name,
                    port_type=port.port_type,
                    display_name=port.display_name,
                    required=port.required,
                    visible=port.visible,
                    tooltip=port.tooltip,
                )
                for port in descriptor.input_ports
            ),
            output_ports=tuple(
                PortManifest(
                    name=port.name,
                    port_type=port.port_type,
                    display_name=port.display_name,
                    required=port.required,
                    visible=port.visible,
                    tooltip=port.tooltip,
                )
                for port in descriptor.output_ports
            ),
            config_schema=dict(descriptor.config_schema),
        )
