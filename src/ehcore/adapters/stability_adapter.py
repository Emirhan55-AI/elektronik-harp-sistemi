"""
Kararlılık Filtresi Adaptörü — Katman C: Doğrulama.

CFAR'dan gelen ham tespitleri zaman boyunca takip eder.
Sadece kararlı (persistent) sinyalleri "onaylı tespit" olarak çıkarır.

Algoritma kodu ehcore.algorithms.detection.stability_tracker modülündedir.
Bu adapter ince bir köprüdür.
"""

from __future__ import annotations

from typing import ClassVar

import numpy as np

from ehcore.algorithms.detection import StabilityTracker
from ehcore.algorithms.detection.cfar import CFARDetection
from ehcore.contracts import (
    DataEnvelope,
    NodeDescriptor,
    PortDef,
    PortType,
)
from ehcore.registry import NodeRegistry

from ._base import BaseAdapter


@NodeRegistry.register
class StabilityFilterAdapter(BaseAdapter):
    """Kararlılık Filtresi — CFAR çıktısını zaman boyunca doğrular."""

    descriptor: ClassVar[NodeDescriptor] = NodeDescriptor(
        node_id="stability_filter",
        display_name="Kararlılık",
        category="Tespit",
        description=(
            "Aday tespitleri zaman boyunca takip eder ve kararlı hedefleri doğrular."
        ),
        input_ports=(
            PortDef(
                name="detections_in",
                port_type=PortType.DETECTIONS,
                display_name="Tespitler",
                tooltip="CFAR tarafından bulunan aday hedefler bu girişe bağlanır.",
            ),
        ),
        output_ports=(
            PortDef(
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
    )

    def __init__(self) -> None:
        super().__init__()
        self._tracker: StabilityTracker | None = None

    def configure(self, config: dict) -> None:
        defaults = self.descriptor.default_config()
        defaults.update(config)
        self._config = defaults

    def start(self) -> None:
        super().start()
        self._tracker = StabilityTracker(
            min_hits=int(self._config.get("min_hits", 5)),
            max_misses=int(self._config.get("max_misses", 3)),
            freq_tolerance_bins=int(self._config.get("freq_tolerance_bins", 4)),
            confirmed_stale_after=float(self._config.get("stale_after_sec", 1.0)),
            confirmed_hold_seconds=float(self._config.get("confirmed_hold_sec", 8.0)),
        )

    def stop(self) -> None:
        super().stop()
        if self._tracker:
            self._tracker.reset()

    def process(
        self,
        inputs: dict[str, DataEnvelope],
    ) -> dict[str, DataEnvelope]:
        """Ham tespitler → onaylı tespitler."""
        det_envelope = inputs.get("detections_in")
        if det_envelope is None or self._tracker is None:
            return {}

        det_array = det_envelope.payload

        # Structured array → CFARDetection listesine dönüştür

        cfar_detections = []
        if det_array.size > 0:
            for row in det_array:
                cfar_detections.append(CFARDetection(
                    bin_index=int(row["bin_index"]),
                    freq_normalized=float(row["freq_normalized"]),
                    power_db=float(row["power_db"]),
                    threshold_db=float(row["threshold_db"]),
                    snr_db=float(row["snr_db"]),
                    bandwidth_bins=int(row["bandwidth_bins"]),
                ))

        # Kararlılık filtresinden geçir
        confirmed = self._tracker.update(
            cfar_detections,
            timestamp=det_envelope.timestamp,
        )

        # Onaylı tespitleri structured array olarak paketle
        if confirmed:
            confirmed_array = np.array(
                [
                    (
                        t.target_id,
                        t.center_freq_normalized,
                        t.center_bin,
                        t.bandwidth_bins,
                        t.power_db,
                        t.snr_db,
                        t.first_seen,
                        t.last_seen,
                        t.hit_count,
                        t.state,
                    )
                    for t in confirmed
                ],
                dtype=[
                    ("target_id", np.int32),
                    ("center_freq_normalized", np.float64),
                    ("center_bin", np.int32),
                    ("bandwidth_bins", np.int32),
                    ("power_db", np.float64),
                    ("snr_db", np.float64),
                    ("first_seen", np.float64),
                    ("last_seen", np.float64),
                    ("hit_count", np.int32),
                    ("state", "U12"),
                ],
            )
        else:
            confirmed_array = np.array(
                [],
                dtype=[
                    ("target_id", np.int32),
                    ("center_freq_normalized", np.float64),
                    ("center_bin", np.int32),
                    ("bandwidth_bins", np.int32),
                    ("power_db", np.float64),
                    ("snr_db", np.float64),
                    ("first_seen", np.float64),
                    ("last_seen", np.float64),
                    ("hit_count", np.int32),
                    ("state", "U12"),
                ],
            )

        result_envelope = det_envelope.clone_header(
            data_type="detection_list",
            payload=confirmed_array,
            metadata={
                **det_envelope.metadata,
                "confirmed_count": len(confirmed),
                "active_tracks": self._tracker.active_tracks,
                "sample_rate": det_envelope.sample_rate,
                "center_freq": det_envelope.center_freq,
            },
        )

        return {"confirmed_out": result_envelope}
