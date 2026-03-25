"""Kaynak blok manifestleri."""

from __future__ import annotations

from ehplatform.catalog.types import NodeManifest, PortManifest
from ehplatform.contracts import PortType


MANIFESTS = (
    NodeManifest(
        node_id="sigmf_source",
        display_name="SigMF Kaynağı",
        category="Kaynaklar",
        description="SigMF dosyasından ham IQ verisini okuyup akışa besler.",
        algorithm_import_path="algorithms.sources.sigmf_source",
        algorithm_class_name="SigMFSourceKernel",
        output_ports=(
            PortManifest(
                name="iq_out",
                port_type=PortType.IQ,
                display_name="IQ",
                tooltip="Kaynaktan okunan ham IQ verisi bu çıkıştan verilir.",
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
                "label": "Blok Boyutu (örnek)",
                "options": [4096, 8192, 16384, 32768, 65536, 131072],
            },
            "loop": {
                "type": "bool",
                "default": True,
                "label": "Döngü (Dosya Sonunda Başa Sar)",
            },
        },
        ui_hints={
            "accent": "source",
            "inspector_section": "source",
        },
    ),
)
