"""ehcore.contracts — Veri sözleşmeleri ve arayüz tanımları."""

from .data_envelope import DataEnvelope
from .port_types import PortType, PortDef, check_port_compatibility
from .node_descriptor import NodeDescriptor

__all__ = [
    "DataEnvelope",
    "PortType",
    "PortDef",
    "check_port_compatibility",
    "NodeDescriptor",
]
