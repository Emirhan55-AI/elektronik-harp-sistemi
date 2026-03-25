"""
Workers — QThread tabanlı arka plan worker'ları.

PipelineWorker: Pipeline engine sinyal köprüsü.
PlotRefreshTimer: Engine'deki son tick çıktılarından veri çekerek
    UI'ya sinyal gönderir. Tüm veri pipeline tick sonuçlarından gelir.
"""

from __future__ import annotations

from PySide6.QtCore import Signal, QTimer, QObject
import numpy as np

from ehplatform.registry import NodeRegistry


class PipelineWorker(QObject):
    """Pipeline engine kontrolünü yöneten sinyal köprüsü."""

    state_changed = Signal(str)        # "idle"/"running"/"error"
    error_occurred = Signal(str, str)   # (node_id, error_msg)
    log_message = Signal(str, str)      # (message, level)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

    def on_state_change(self, state: str) -> None:
        self.state_changed.emit(state)

    def on_error(self, node_id: str, msg: str) -> None:
        self.error_occurred.emit(node_id, msg)
        self.log_message.emit(msg, "error")


class PlotRefreshTimer(QObject):
    """
    Periyodik grafik güncelleme zamanlayıcısı.

    Engine'deki her tick sonucundan veri çeker:
    - STFT İşleyici çıkışından: PSD → Spektrum, Waterfall
    - CFAR Tespiti çıkışından: Eşik eğrisi, Ham tespitler
    - Kararlılık Filtresi çıkışından: Onaylı tespitler
    """

    # Spektrum ve waterfall
    fft_data_ready = Signal(np.ndarray, float, float)        # (psd_db, center_freq, sample_rate)
    waterfall_data_ready = Signal(np.ndarray, float, float)  # (psd_db, center_freq, sample_rate)

    # CFAR overlay
    threshold_data_ready = Signal(np.ndarray, float, float)  # (threshold_db, center_freq, sample_rate)
    cfar_detections_ready = Signal(np.ndarray, float, float) # (det_structured_array, center_freq, sample_rate)

    # Onaylı tespitler
    confirmed_targets_ready = Signal(np.ndarray, float, float, int)  # (confirmed_structured_array, center_freq, sample_rate, fft_size)

    def __init__(self, interval_ms: int = 50, parent=None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._refresh)
        self._engine = None
        self._last_timestamps: dict[str, float] = {}  # "node_id:port_name" -> timestamp

    def set_engine(self, engine) -> None:
        """Pipeline engine referansını ayarla."""
        self._engine = engine

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._last_timestamps.clear()

    def _refresh(self) -> None:
        """
        Engine'deki adapter'lardan son çıktıları çek ve UI'ya sinyal gönder.

        Pipeline engine her tick'te tüm node'ları sırayla çalıştırır.
        Biz burada her adapter'ın data_type'ına bakarak ilgili sinyali yayınlarız.
        """
        if self._engine is None:
            return

        # Engine'in kendi arka plan thread'i node'ları çalıştırır.
        # Biz burada sadece son üretilen çıktıları okuruz.
        engine = self._engine
        if engine is None:
            return

        outputs = engine.last_outputs

        if not outputs:
            return

        for node_id, node_outputs in outputs.items():
            graph_node = engine.graph.get_node(node_id)
            manifest = None
            if graph_node is not None:
                manifest = NodeRegistry.get_manifest(graph_node.node_type_id)

            for port_name, envelope in node_outputs.items():
                # Stale (eski) veri kontrolü
                key = f"{node_id}:{port_name}"
                if self._last_timestamps.get(key) == envelope.timestamp:
                    continue
                self._last_timestamps[key] = envelope.timestamp

                cf = envelope.center_freq
                sr = envelope.sample_rate
                bindings = ()
                if manifest is not None:
                    bindings = tuple(
                        binding
                        for binding in manifest.visualization_bindings
                        if binding.port_name == port_name
                    )

                if bindings:
                    for binding in bindings:
                        self._emit_binding(binding.view_id, envelope, cf, sr, binding.metadata_key)
                    continue

                self._emit_fallback(envelope, port_name, cf, sr)

    def _emit_binding(
        self,
        view_id: str,
        envelope,
        center_freq: float,
        sample_rate: float,
        metadata_key: str = "",
    ) -> None:
        if view_id == "spectrum":
            self.fft_data_ready.emit(envelope.payload, center_freq, sample_rate)
            return

        if view_id == "waterfall":
            row = envelope.metadata.get(metadata_key) if metadata_key else envelope.payload
            if not isinstance(row, np.ndarray):
                row = envelope.payload
            self.waterfall_data_ready.emit(row, center_freq, sample_rate)
            return

        if view_id == "threshold_overlay":
            self.threshold_data_ready.emit(envelope.payload, center_freq, sample_rate)
            return

        if view_id == "cfar_detections":
            self.cfar_detections_ready.emit(envelope.payload, center_freq, sample_rate)
            return

        if view_id == "confirmed_targets":
            fft_size = int(envelope.metadata.get("fft_size", 0))
            self.confirmed_targets_ready.emit(
                envelope.payload,
                center_freq,
                sample_rate,
                fft_size,
            )

    def _emit_fallback(self, envelope, port_name: str, center_freq: float, sample_rate: float) -> None:
        data_type = envelope.data_type
        if data_type == "fft_frame":
            if port_name == "threshold_out":
                self.threshold_data_ready.emit(envelope.payload, center_freq, sample_rate)
            else:
                self.fft_data_ready.emit(envelope.payload, center_freq, sample_rate)
                waterfall_row = envelope.metadata.get("waterfall_row")
                if isinstance(waterfall_row, np.ndarray):
                    self.waterfall_data_ready.emit(waterfall_row, center_freq, sample_rate)
                else:
                    self.waterfall_data_ready.emit(envelope.payload, center_freq, sample_rate)
            return

        if data_type == "detections":
            self.cfar_detections_ready.emit(envelope.payload, center_freq, sample_rate)
            return

        if data_type == "detection_list":
            fft_size = int(envelope.metadata.get("fft_size", 0))
            self.confirmed_targets_ready.emit(
                envelope.payload,
                center_freq,
                sample_rate,
                fft_size,
            )


