"""
Workers — QThread tabanlı arka plan worker'ları.

PipelineWorker: Pipeline engine'i ayrı thread'de çalıştırır.
PlotRefreshWorker: Periyodik olarak viewer adapter'dan veri çekerek
    UI'ya sinyal gönderir.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal, QTimer, QObject
import numpy as np


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
    Periyodik grafik güncelleme zamanlayıcıSı.

    Viewer adapter'dan veri çeker ve sinyallerle UI'ya iletir.
    """

    fft_data_ready = Signal(np.ndarray, float, float)    # (fft_db, center_freq, sample_rate)
    waterfall_data_ready = Signal(np.ndarray, float, float)
    iq_data_ready = Signal(np.ndarray)

    def __init__(self, interval_ms: int = 50, parent=None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._refresh)
        self._engine = None

    def set_engine(self, engine) -> None:
        """Pipeline engine referansını ayarla."""
        self._engine = engine

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _refresh(self) -> None:
        """Adapter'lardan veri çek ve sinyal gönder."""
        if self._engine is None:
            return

        for node_id, adapter in self._engine.adapters.items():
            # Viewer adapter'dan veri çek
            if hasattr(adapter, "get_latest_fft"):
                fft_env = adapter.get_latest_fft()
                if fft_env is not None:
                    self.fft_data_ready.emit(
                        fft_env.payload,
                        fft_env.center_freq,
                        fft_env.sample_rate,
                    )
                    self.waterfall_data_ready.emit(
                        fft_env.payload,
                        fft_env.center_freq,
                        fft_env.sample_rate,
                    )

            # Source adapter'dan IQ veri (son üretilen)
            if hasattr(adapter, "_generate_simulated"):
                # SourceAdapter — son çıktıda iq_out var mı kontrol et
                pass  # IQ veri engine tick sonuçlarından gelir
