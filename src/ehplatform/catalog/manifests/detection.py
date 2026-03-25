"""Tespit ve izleme blok manifestleri."""

from __future__ import annotations

from ehplatform.catalog.types import NodeManifest, PortManifest, VisualizationBinding
from ehplatform.contracts import PortType


MANIFESTS = (
    NodeManifest(
        node_id="cfar_detector",
        display_name="CFAR",
        category="Tespit",
        description="Spektrum üzerinde gürültü tabanına göre aday sinyalleri ayıklar.",
        algorithm_import_path="algorithms.detection.cfar",
        algorithm_class_name="CFARKernel",
        input_ports=(
            PortManifest(
                name="fft_in",
                port_type=PortType.FFT,
                display_name="FFT",
                tooltip="STFT çıkışındaki spektrum bu girişe bağlanır.",
            ),
        ),
        output_ports=(
            PortManifest(
                name="detections_out",
                port_type=PortType.DETECTIONS,
                display_name="Tespitler",
                tooltip="Bulunan aday hedefler bu çıkıştan verilir.",
            ),
            PortManifest(
                name="threshold_out",
                port_type=PortType.FFT,
                display_name="Eşik",
                required=False,
                visible=False,
                tooltip="Spektrumdaki eşik eğrisini besleyen iç çıkış.",
            ),
        ),
        config_schema={
            "num_guard_cells": {
                "type": "int",
                "default": 4,
                "label": "Guard Hücre Sayısı",
            },
            "num_reference_cells": {
                "type": "int",
                "default": 16,
                "label": "Referans Hücre Sayısı",
            },
            "threshold_factor_db": {
                "type": "float",
                "default": 6.0,
                "label": "Eşik Faktörü (dB)",
            },
        },
        visualization_bindings=(
            VisualizationBinding(port_name="detections_out", view_id="cfar_detections"),
            VisualizationBinding(port_name="threshold_out", view_id="threshold_overlay"),
        ),
    ),
    NodeManifest(
        node_id="stability_filter",
        display_name="Kararlılık",
        category="Tespit",
        description="Aday tespitleri zaman boyunca takip eder ve kararlı hedefleri doğrular.",
        algorithm_import_path="algorithms.tracking.stability_tracker",
        algorithm_class_name="StabilityFilterKernel",
        input_ports=(
            PortManifest(
                name="detections_in",
                port_type=PortType.DETECTIONS,
                display_name="Tespitler",
                tooltip="CFAR tarafından bulunan aday hedefler bu girişe bağlanır.",
            ),
        ),
        output_ports=(
            PortManifest(
                name="confirmed_out",
                port_type=PortType.DETECTION_LIST,
                display_name="Onaylı",
                tooltip="Zaman içinde doğrulanmış hedefler bu çıkıştan verilir.",
            ),
        ),
        config_schema={
            "min_hits": {
                "type": "int",
                "default": 5,
                "label": "Min. Ardışık Tespit (onay için)",
            },
            "max_misses": {
                "type": "int",
                "default": 3,
                "label": "Maks. Kaçırma Toleransı",
            },
            "freq_tolerance_bins": {
                "type": "int",
                "default": 4,
                "label": "Frekans Eşleştirme Toleransı (bin)",
            },
            "stale_after_sec": {
                "type": "float",
                "default": 1.0,
                "label": "Stale Durum Gecikmesi (sn)",
            },
            "confirmed_hold_sec": {
                "type": "float",
                "default": 8.0,
                "label": "Onaylı Hedef Tutma Süresi (sn)",
            },
        },
        visualization_bindings=(
            VisualizationBinding(port_name="confirmed_out", view_id="confirmed_targets"),
        ),
    ),
)
