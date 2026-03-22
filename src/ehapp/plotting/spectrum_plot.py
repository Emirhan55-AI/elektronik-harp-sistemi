"""
SpectrumPlot — Canlı FFT spektrum grafiği.

Özellikler:
- Canlı eğri
- Peak hold
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
    """Canlı FFT spektrum grafiği."""

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

        # Canlı eğri
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(COLORS["plot_line1"], width=1.5),
            name="Spektrum",
        )

        # Peak hold
        self._peak_curve = self._plot_widget.plot(
            pen=pg.mkPen(COLORS["plot_peak"], width=1, style=pg.QtCore.Qt.PenStyle.DashLine),
            name="Peak Hold",
        )
        self._peak_data: np.ndarray | None = None

        # Marker
        self._marker = pg.InfiniteLine(
            angle=90, movable=True,
            pen=pg.mkPen(COLORS["plot_marker"], width=1, style=pg.QtCore.Qt.PenStyle.DotLine),
        )
        self._plot_widget.addItem(self._marker)

        # Cursor readout
        self._cursor_label = pg.TextItem(
            text="", color=COLORS["text_primary"],
            anchor=(0, 1),
        )
        self._plot_widget.addItem(self._cursor_label)
        self._cursor_label.setPos(0, 0)

        self._marker.sigPositionChanged.connect(self._update_cursor)
        self._freq_axis: np.ndarray | None = None

    def update_data(
        self,
        fft_db: np.ndarray,
        center_freq: float = 0.0,
        sample_rate: float = 1.0,
    ) -> None:
        """FFT verisini güncelle."""
        n = len(fft_db)
        freqs = np.linspace(
            (center_freq - sample_rate / 2) / 1e6,
            (center_freq + sample_rate / 2) / 1e6,
            n,
        )
        self._freq_axis = freqs

        self._curve.setData(freqs, fft_db)

        # Peak hold güncelle
        if self._peak_data is None or len(self._peak_data) != n:
            self._peak_data = fft_db.copy()
        else:
            self._peak_data = np.maximum(self._peak_data, fft_db)
        self._peak_curve.setData(freqs, self._peak_data)

    def reset(self) -> None:
        """Grafiği sıfırla."""
        self._curve.setData([], [])
        self._peak_curve.setData([], [])
        self._peak_data = None
        self._freq_axis = None
        self._plot_widget.autoRange()

    def _update_cursor(self) -> None:
        """Marker pozisyonunda readout güncelle."""
        freq = self._marker.value()
        self._cursor_label.setText(f"{freq:.3f} MHz")
        self._cursor_label.setPos(freq, self._plot_widget.viewRange()[1][1])

    def set_marker_freq(self, freq_mhz: float) -> None:
        """Marker'ı belirli frekansa taşı (MHz)."""
        self._marker.setValue(freq_mhz)
