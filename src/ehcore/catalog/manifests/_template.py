"""AI ve sistem entegrasyonu icin ornek manifest sablonu.

Bu dosya import edilmez. Yalnizca kopyalanip yeni manifest modulu olusturmak icindir.
"""

from ehcore.contracts import PortType

from ehcore.catalog.types import NodeManifest, PortManifest, VisualizationBinding


MANIFESTS = (
    NodeManifest(
        node_id="ornek_node",
        display_name="Ornek Blok",
        category="Tespit",
        description="Bu aciklama kullaniciya blok ne yaptigini anlatir.",
        algorithm_import_path="ehcore.algorithms.detection.ornek",
        algorithm_class_name="OrnekKernel",
        input_ports=(
            PortManifest(
                name="fft_in",
                port_type=PortType.FFT,
                display_name="FFT",
                tooltip="Bu blok FFT girdisi bekler.",
            ),
        ),
        output_ports=(
            PortManifest(
                name="detections_out",
                port_type=PortType.DETECTIONS,
                display_name="Tespitler",
                tooltip="Bulunan aday hedefler bu cikistan verilir.",
            ),
        ),
        config_schema={
            "threshold_db": {
                "type": "float",
                "default": 8.0,
                "label": "Esik (dB)",
            },
        },
        visualization_bindings=(
            VisualizationBinding(port_name="detections_out", view_id="cfar_detections"),
        ),
    ),
)
