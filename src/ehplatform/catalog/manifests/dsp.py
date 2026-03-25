"""Ön işleme blok manifestleri."""

from __future__ import annotations

from ehplatform.catalog.types import NodeManifest, PortManifest, VisualizationBinding
from ehplatform.contracts import PortType


MANIFESTS = (
    NodeManifest(
        node_id="stft_processor",
        display_name="STFT",
        category="Ön İşleme",
        description="IQ verisini frekans düzlemine çevirir ve spektrum üretir.",
        algorithm_import_path="algorithms.dsp.stft",
        algorithm_class_name="STFTKernel",
        input_ports=(
            PortManifest(
                name="iq_in",
                port_type=PortType.IQ,
                display_name="IQ",
                tooltip="Ham IQ verisi bu girişten alınır.",
            ),
        ),
        output_ports=(
            PortManifest(
                name="fft_out",
                port_type=PortType.FFT,
                display_name="FFT",
                tooltip="İşlenmiş frekans spektrumu bu çıkıştan verilir.",
            ),
        ),
        config_schema={
            "fft_size": {
                "type": "int",
                "default": 1024,
                "label": "FFT Boyutu",
                "options": [256, 512, 1024, 2048, 4096, 8192],
            },
            "window": {
                "type": "str",
                "default": "hann",
                "label": "Pencere Fonksiyonu",
                "options": ["hann", "hamming", "blackman", "none"],
            },
            "remove_dc": {
                "type": "bool",
                "default": True,
                "label": "DC Ofset Temizle",
            },
        },
        visualization_bindings=(
            VisualizationBinding(port_name="fft_out", view_id="spectrum"),
            VisualizationBinding(
                port_name="fft_out",
                view_id="waterfall",
                metadata_key="waterfall_row",
            ),
        ),
    ),
)
