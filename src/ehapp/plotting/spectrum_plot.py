"""
SpectrumPlot — Canlı FFT spektrum grafiği + CFAR overlay.

Özellikler:
- Canlı PSD eğrisi (Welch çıkışı)
- Peak hold
- CFAR eşik eğrisi (kırmızı kesikli çizgi)
- Tespit marker'ları (sarı elmas)
- Cursor readout
- Autorange / reset
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget
from PySide6.QtGui import QColor

from ehapp.theme.tokens import COLORS
from ehapp.strings.tr import PLOT_SPECTRUM, PLOT_FREQUENCY_LABEL, PLOT_POWER_LABEL


class SpectrumPlot(QWidget):
    """Canlı FFT spektrum grafiği + CFAR eşik overlay."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # pyqtgraph ayarları
        pg.setConfigOptions(antialias=True, background=COLORS["plot_bg"])

        self._plot_widget = pg.PlotWidget(title=PLOT_SPECTRUM)
        self._plot_widget.setLabel("bottom", PLOT_FREQUENCY_LABEL)
        self._plot_widget.setLabel("left", PLOT_POWER_LABEL)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self._plot_widget.getAxis("bottom").setPen(pg.mkPen(COLORS["text_secondary"]))
        self._plot_widget.getAxis("left").setPen(pg.mkPen(COLORS["text_secondary"]))
        layout.addWidget(self._plot_widget)

        # Legend
        self._legend = self._plot_widget.addLegend(offset=(-10, 10))

        # 1. Canlı PSD eğrisi
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(COLORS["plot_line1"], width=1.5),
            name="Spektrum",
        )

        # 2. Peak hold
        self._peak_curve = self._plot_widget.plot(
            pen=pg.mkPen(COLORS["plot_peak"], width=1, style=pg.QtCore.Qt.PenStyle.DashLine),
            name="Peak Hold",
        )
        self._peak_data: np.ndarray | None = None

        # 3. CFAR eşik eğrisi
        self._threshold_curve = self._plot_widget.plot(
            pen=pg.mkPen(
                COLORS["plot_threshold"], width=1.5,
                style=pg.QtCore.Qt.PenStyle.DashDotLine,
            ),
            name="CFAR Eşik",
        )

        # 4. Tespit marker'ları (scatter plot)
        self._det_scatter = pg.ScatterPlotItem(
            size=10,
            symbol="d",  # Elmas
            brush=pg.mkBrush(COLORS["plot_detection_marker"]),
            pen=pg.mkPen(None),
        )
        self._plot_widget.addItem(self._det_scatter)

        # 5. Marker (dikey çizgi — cursor)
        self._marker = pg.InfiniteLine(
            angle=90, movable=True,
            pen=pg.mkPen(COLORS["plot_marker"], width=1, style=pg.QtCore.Qt.PenStyle.DotLine),
        )
        self._plot_widget.addItem(self._marker)

        # 6. Cursor readout
        self._cursor_label = pg.TextItem(
            text="", color=COLORS["text_primary"],
            anchor=(0, 1),
        )
        self._plot_widget.addItem(self._cursor_label)
        self._cursor_label.setPos(0, 0)

        self._marker.sigPositionChanged.connect(self._update_cursor)
        self._freq_axis: np.ndarray | None = None
        self._last_psd: np.ndarray | None = None

    def update_data(
        self,
        fft_db: np.ndarray,
        center_freq: float = 0.0,
        sample_rate: float = 1.0,
    ) -> None:
        """FFT/PSD verisini güncelle."""
        n = len(fft_db)
        freq_min = (center_freq - sample_rate / 2) / 1e6
        freq_max = (center_freq + sample_rate / 2) / 1e6

        freqs = np.linspace(freq_min, freq_max, n)

        # İlk veri geldiğinde otomatik odakla
        is_first = self._freq_axis is None

        self._freq_axis = freqs
        self._last_psd = fft_db
        self._curve.setData(freqs, fft_db)

        if is_first:
            self._plot_widget.setXRange(freq_min, freq_max, padding=0.05)

        # Peak hold güncelle
        if self._peak_data is None or len(self._peak_data) != n:
            self._peak_data = fft_db.copy()
        else:
            self._peak_data = np.maximum(self._peak_data, fft_db)
        self._peak_curve.setData(freqs, self._peak_data)

    def update_threshold(
        self,
        threshold_db: np.ndarray,
        center_freq: float = 0.0,
        sample_rate: float = 1.0,
    ) -> None:
        """CFAR eşik eğrisini güncelle (overlay)."""
        n = len(threshold_db)
        freqs = np.linspace(
            (center_freq - sample_rate / 2) / 1e6,
            (center_freq + sample_rate / 2) / 1e6,
            n,
        )
        self._threshold_curve.setData(freqs, threshold_db)

    def update_detections(
        self,
        det_array: np.ndarray,
        center_freq: float = 0.0,
        sample_rate: float = 1.0,
    ) -> None:
        """
        CFAR tespit noktalarını marker olarak göster.

        det_array: structured array with 'freq_normalized' and 'power_db' fields.
        """
        if det_array.size == 0:
            self._det_scatter.setData([], [])
            return

        freqs_hz = det_array["freq_normalized"] * sample_rate + center_freq
        freqs_mhz = freqs_hz / 1e6
        powers = det_array["power_db"]

        self._det_scatter.setData(freqs_mhz, powers)

    def reset(self) -> None:
        """Grafiği sıfırla."""
        self._curve.setData([], [])
        self._peak_curve.setData([], [])
        self._threshold_curve.setData([], [])
        self._det_scatter.setData([], [])
        self._peak_data = None
        self._freq_axis = None
        self._last_psd = None
        self._plot_widget.autoRange()

    def _update_cursor(self) -> None:
        """Marker pozisyonunda readout güncelle."""
        freq = self._marker.value()
        power_text = ""
        if self._freq_axis is not None and self._last_psd is not None:
            idx = np.searchsorted(self._freq_axis, freq)
            idx = np.clip(idx, 0, len(self._last_psd) - 1)
            power_text = f"  {self._last_psd[idx]:.1f} dB"

        self._cursor_label.setText(f"{freq:.3f} MHz{power_text}")
        self._cursor_label.setPos(freq, self._plot_widget.viewRange()[1][1])

    def set_marker_freq(self, freq_mhz: float) -> None:
        """Marker'ı belirli frekansa taşı (MHz)."""
        self._marker.setValue(freq_mhz)
