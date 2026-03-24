"""Tespit ve izleme blok manifestleri."""

from __future__ import annotations

from ehcore.contracts import PortType

from ehcore.catalog.types import NodeManifest, PortManifest, VisualizationBinding


MANIFESTS = (
    NodeManifest(
        node_id="cfar_detector",
        display_name="CFAR",
        category="Tespit",
        description="Spektrum uzerinde gurultu tabanina gore aday sinyalleri ayiklar.",
        algorithm_import_path="ehcore.algorithms.detection.cfar",
        algorithm_class_name="CFARKernel",
        input_ports=(
            PortManifest(
                name="fft_in",
                port_type=PortType.FFT,
                display_name="FFT",
                tooltip="STFT cikisindaki spektrum bu girise baglanir.",
            ),
        ),
        output_ports=(
            PortManifest(
                name="detections_out",
                port_type=PortType.DETECTIONS,
                display_name="Tespitler",
                tooltip="Bulunan aday hedefler bu cikistan verilir.",
            ),
            PortManifest(
                name="threshold_out",
                port_type=PortType.FFT,
                display_name="Esik",
                required=False,
                visible=False,
                tooltip="Spektrumdaki esik egrisini besleyen ic cikis.",
            ),
        ),
        config_schema={
            "num_guard_cells": {
                "type": "int",
                "default": 4,
                "label": "Guard Hucre Sayisi",
            },
            "num_reference_cells": {
                "type": "int",
                "default": 16,
                "label": "Referans Hucre Sayisi",
            },
            "threshold_factor_db": {
                "type": "float",
                "default": 6.0,
                "label": "Esik Faktoru (dB)",
            },
        },
        visualization_bindings=(
            VisualizationBinding(port_name="detections_out", view_id="cfar_detections"),
            VisualizationBinding(port_name="threshold_out", view_id="threshold_overlay"),
        ),
    ),
    NodeManifest(
        node_id="stability_filter",
        display_name="Kararlilik",
        category="Tespit",
        description="Aday tespitleri zaman boyunca takip eder ve kararli hedefleri dogrular.",
        algorithm_import_path="ehcore.algorithms.detection.stability_tracker",
        algorithm_class_name="StabilityFilterKernel",
        input_ports=(
            PortManifest(
                name="detections_in",
                port_type=PortType.DETECTIONS,
                display_name="Tespitler",
                tooltip="CFAR tarafindan bulunan aday hedefler bu girise baglanir.",
            ),
        ),
        output_ports=(
            PortManifest(
                name="confirmed_out",
                port_type=PortType.DETECTION_LIST,
                display_name="Onayli",
                tooltip="Zaman icinde dogrulanmis hedefler bu cikistan verilir.",
            ),
        ),
        config_schema={
            "min_hits": {
                "type": "int",
                "default": 5,
                "label": "Min. Ardisik Tespit (onay icin)",
            },
            "max_misses": {
                "type": "int",
                "default": 3,
                "label": "Maks. Kacirma Toleransi",
            },
            "freq_tolerance_bins": {
                "type": "int",
                "default": 4,
                "label": "Frekans Eslestirme Toleransi (bin)",
            },
            "stale_after_sec": {
                "type": "float",
                "default": 1.0,
                "label": "Stale Durum Gecikmesi (sn)",
            },
            "confirmed_hold_sec": {
                "type": "float",
                "default": 8.0,
                "label": "Onayli Hedef Tutma Suresi (sn)",
            },
        },
        visualization_bindings=(
            VisualizationBinding(port_name="confirmed_out", view_id="confirmed_targets"),
        ),
    ),
)
