"""On isleme blok manifestleri."""

from __future__ import annotations

from ehcore.contracts import PortType

from ehcore.catalog.types import NodeManifest, PortManifest, VisualizationBinding


MANIFESTS = (
    NodeManifest(
        node_id="stft_processor",
        display_name="STFT",
        category="On Isleme",
        description="IQ verisini frekans duzlemine cevirir ve spektrum uretir.",
        algorithm_import_path="ehcore.algorithms.dsp.stft",
        algorithm_class_name="STFTKernel",
        input_ports=(
            PortManifest(
                name="iq_in",
                port_type=PortType.IQ,
                display_name="IQ",
                tooltip="Ham IQ verisi bu giristen alinir.",
            ),
        ),
        output_ports=(
            PortManifest(
                name="fft_out",
                port_type=PortType.FFT,
                display_name="FFT",
                tooltip="Islenmis frekans spektrumu bu cikistan verilir.",
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
            VisualizationBinding(port_name="fft_out", view_id="waterfall", metadata_key="waterfall_row"),
        ),
    ),
)
