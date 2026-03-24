"""
CFAR Tespit Adaptörü — Katman B: Adaptif Eşikleme.

PSD (FFT) çıkışını alır, CA-CFAR uygular ve ham tespitleri üretir.
Eşik eğrisi ve tespit maskesi de çıkış olarak sunulur.

Algoritma kodu ehcore.algorithms.detection.cfar modülündedir.
Bu adapter ince bir köprüdür.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np

from ehcore.algorithms.detection import ca_cfar
from ehcore.contracts import (
    DataEnvelope,
    NodeDescriptor,
    PortDef,
    PortType,
)
from ehcore.registry import NodeRegistry

from ._base import BaseAdapter


@NodeRegistry.register
class CFARAdapter(BaseAdapter):
    """CFAR Tespit — PSD üzerinde adaptif eşikleme."""

    descriptor: ClassVar[NodeDescriptor] = NodeDescriptor(
        node_id="cfar_detector",
        display_name="CFAR Tespiti",
        category="Tespit",
        description="CA-CFAR ile gürültü tabanına göre sinyal tespiti yapar.",
        input_ports=(
            PortDef(name="fft_in", port_type=PortType.FFT, display_name="PSD Giriş"),
        ),
        output_ports=(
            PortDef(
                name="detections_out",
                port_type=PortType.DETECTIONS,
                display_name="Ham Tespitler",
            ),
            PortDef(
                name="threshold_out",
                port_type=PortType.FFT,
                display_name="Eşik Eğrisi",
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
    )

    def configure(self, config: dict) -> None:
        defaults = self.descriptor.default_config()
        defaults.update(config)
        self._config = defaults

    def process(
        self,
        inputs: dict[str, DataEnvelope],
    ) -> dict[str, DataEnvelope]:
        """PSD → CFAR tespitleri + eşik eğrisi."""
        fft_envelope = inputs.get("fft_in")
        if fft_envelope is None:
            return {}

        psd_db = fft_envelope.payload

        guard = int(self._config.get("num_guard_cells", 4))
        ref = int(self._config.get("num_reference_cells", 16))
        threshold = float(self._config.get("threshold_factor_db", 6.0))

        # CA-CFAR çalıştır
        result = ca_cfar(
            psd_db,
            num_guard_cells=guard,
            num_reference_cells=ref,
            threshold_factor_db=threshold,
            merge_adjacent=True,
        )

        # Tespitleri structured array olarak paketle
        if result.detections:
            det_array = np.array(
                [
                    (
                        d.bin_index,
                        d.freq_normalized,
                        d.power_db,
                        d.threshold_db,
                        d.snr_db,
                        d.bandwidth_bins,
                    )
                    for d in result.detections
                ],
                dtype=[
                    ("bin_index", np.int32),
                    ("freq_normalized", np.float64),
                    ("power_db", np.float64),
                    ("threshold_db", np.float64),
                    ("snr_db", np.float64),
                    ("bandwidth_bins", np.int32),
                ],
            )
        else:
            det_array = np.array(
                [],
                dtype=[
                    ("bin_index", np.int32),
                    ("freq_normalized", np.float64),
                    ("power_db", np.float64),
                    ("threshold_db", np.float64),
                    ("snr_db", np.float64),
                    ("bandwidth_bins", np.int32),
                ],
            )

        # Tespit zarfı
        det_envelope = fft_envelope.clone_header(
            data_type="detections",
            payload=det_array,
            metadata={
                **fft_envelope.metadata,
                "detection_count": result.count,
                "cfar_guard": guard,
                "cfar_ref": ref,
                "cfar_threshold_db": threshold,
            },
        )

        # Eşik eğrisi zarfı (PSD üzerinde overlay olarak çizilecek)
        threshold_envelope = fft_envelope.clone_header(
            data_type="fft_frame",
            payload=result.threshold_curve,
        )

        return {
            "detections_out": det_envelope,
            "threshold_out": threshold_envelope,
        }
