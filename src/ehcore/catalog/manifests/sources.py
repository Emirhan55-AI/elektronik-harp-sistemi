"""Kaynak blok manifestleri."""

from __future__ import annotations

from ehcore.contracts import PortType

from ehcore.catalog.types import NodeManifest, PortManifest


MANIFESTS = (
    NodeManifest(
        node_id="sigmf_source",
        display_name="SigMF Kaynagi",
        category="Kaynaklar",
        description="SigMF dosyasindan ham IQ verisini okuyup akisa besler.",
        algorithm_import_path="ehcore.algorithms.sources.sigmf_source",
        algorithm_class_name="SigMFSourceKernel",
        output_ports=(
            PortManifest(
                name="iq_out",
                port_type=PortType.IQ,
                display_name="IQ",
                tooltip="Kaynaktan okunan ham IQ verisi bu cikistan verilir.",
            ),
        ),
        config_schema={
            "file_path": {
                "type": "file",
                "default": "",
                "label": "SigMF Dosya Yolu",
                "required": True,
            },
            "block_size": {
                "type": "int",
                "default": 65536,
                "label": "Blok Boyutu (sample)",
                "options": [4096, 8192, 16384, 32768, 65536, 131072],
            },
            "loop": {
                "type": "bool",
                "default": True,
                "label": "Dongu (Dosya Sonunda Basa Sar)",
            },
        },
        ui_hints={
            "accent": "source",
            "inspector_section": "source",
        },
    ),
)
