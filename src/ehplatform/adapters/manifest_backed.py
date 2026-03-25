"""
Manifest tabanlı generic adapter.

Algoritma dosyaları yalnızca kernel sözleşmesini uygular; UI/runtime köprüsü
bu adapter tarafından sağlanır.
"""

from __future__ import annotations

import importlib
from types import MappingProxyType
from typing import ClassVar

from algorithms import (
    AlgorithmContext,
    AlgorithmKernel,
    AlgorithmPacket,
)
from ehplatform.catalog.types import NodeManifest
from ehplatform.contracts import DataEnvelope, PortType

from ._base import BaseAdapter

_PORT_TYPE_TO_DATA_TYPE = {
    PortType.IQ: "iq_block",
    PortType.FFT: "fft_frame",
    PortType.SPECTROGRAM: "spectrogram",
    PortType.WATERFALL: "waterfall_row",
    PortType.DETECTIONS: "detections",
    PortType.DETECTION_LIST: "detection_list",
    PortType.ANY: "iq_block",
}


class ManifestBackedAdapter(BaseAdapter):
    """NodeManifest tanımından beslenen generic adapter."""

    manifest: ClassVar[NodeManifest]
    descriptor: ClassVar = None

    def __init__(self) -> None:
        super().__init__()
        self._kernel: AlgorithmKernel = self._create_kernel()

    @classmethod
    def configure_class(cls) -> None:
        cls.descriptor = cls.manifest.to_descriptor()

    def configure(self, config: dict) -> None:
        defaults = self.descriptor.default_config()
        defaults.update(config)
        self._config = defaults
        self._kernel.configure(defaults)

    def start(self) -> None:
        super().start()
        self._kernel.start()

    def stop(self) -> None:
        try:
            self._kernel.stop()
        finally:
            super().stop()

    def reset(self) -> None:
        try:
            self._kernel.reset()
        finally:
            super().reset()

    def process(self, inputs: dict[str, DataEnvelope]) -> dict[str, DataEnvelope]:
        context = AlgorithmContext(
            node_id=self.node_instance_id,
            tick_id=self.tick_id,
            runtime_state=self.state,
            variables=MappingProxyType(dict(self.variables)),
            metrics=self.metrics_snapshot(),
        )
        packet_inputs = {
            port_name: self._packet_from_envelope(envelope)
            for port_name, envelope in inputs.items()
        }
        packet_outputs = self._kernel.process(packet_inputs, context)
        return {
            port_name: self._envelope_from_packet(port_name, packet)
            for port_name, packet in packet_outputs.items()
        }

    def _create_kernel(self) -> AlgorithmKernel:
        module = importlib.import_module(self.manifest.algorithm_import_path)
        kernel_cls = getattr(module, self.manifest.algorithm_class_name)
        return kernel_cls()

    @staticmethod
    def _packet_from_envelope(envelope: DataEnvelope) -> AlgorithmPacket:
        return AlgorithmPacket(
            payload=envelope.payload,
            timestamp=envelope.timestamp,
            center_freq=envelope.center_freq,
            sample_rate=envelope.sample_rate,
            metadata=dict(envelope.metadata),
        )

    def _envelope_from_packet(self, port_name: str, packet: AlgorithmPacket) -> DataEnvelope:
        port_def = self.descriptor.get_output_port(port_name)
        if port_def is None:
            raise KeyError(f"Tanımsız output portu: {port_name}")

        data_type = _PORT_TYPE_TO_DATA_TYPE[port_def.port_type]
        return DataEnvelope(
            data_type=data_type,
            payload=packet.payload,
            timestamp=packet.timestamp,
            source_id=self.node_instance_id or self.manifest.node_id,
            center_freq=packet.center_freq,
            sample_rate=packet.sample_rate,
            metadata=dict(packet.metadata),
        )


def build_manifest_adapter_class(manifest: NodeManifest) -> type[ManifestBackedAdapter]:
    """Manifest için yeni bir adapter sınıfı üret."""

    class _GeneratedManifestAdapter(ManifestBackedAdapter):
        pass

    _GeneratedManifestAdapter.__name__ = f"{manifest.node_id.title().replace('_', '')}Adapter"
    _GeneratedManifestAdapter.manifest = manifest
    _GeneratedManifestAdapter.configure_class()
    return _GeneratedManifestAdapter


