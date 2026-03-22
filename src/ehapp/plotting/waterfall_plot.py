"""
WaterfallPlot — Gerçek waterfall/spectrogram görünümü.

pyqtgraph ImageItem ile sıcaklık haritası gösterimi.
Dinamik seviye hesaplama, frekans ekseni.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ehapp.theme.tokens import COLORS
from ehapp.strings.tr import PLOT_WATERFALL, PLOT_FREQUENCY_LABEL


class WaterfallPlot(QWidget):
    """Waterfall / spectrogram grafiği."""

    def __init__(self, max_rows: int = 200, parent=None) -> None:
        super().__init__(parent)
        self._max_rows = max_rows
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOptions(antialias=True, background=COLORS["plot_bg"])

        self._plot_widget = pg.PlotWidget(title=PLOT_WATERFALL)
        self._plot_widget.setLabel("bottom", PLOT_FREQUENCY_LABEL)
        self._plot_widget.setLabel("left", "Zaman (satır)")
        self._plot_widget.getAxis("bottom").setPen(pg.mkPen(COLORS["text_secondary"]))
        self._plot_widget.getAxis("left").setPen(pg.mkPen(COLORS["text_secondary"]))
        layout.addWidget(self._plot_widget)

        # Image item — waterfall heatmap
        self._image = pg.ImageItem()
        self._plot_widget.addItem(self._image)

        # Renk haritası (viridis benzeri)
        cmap = pg.colormap.get("viridis")
        self._lut = cmap.getLookupTable(nPts=256)
        self._image.setLookupTable(self._lut)

        # Veri buffer
        self._buffer: np.ndarray | None = None
        self._row_index = 0
        self._fft_size = 0

        # Seviye
        self._level_min = -80.0
        self._level_max = 0.0

    def update_data(
        self,
        fft_db: np.ndarray,
        center_freq: float = 0.0,
        sample_rate: float = 1.0,
    ) -> None:
        """Yeni satır ekle."""
        n = len(fft_db)

        # Buffer oluştur veya yeniden boyutlandır
        if self._buffer is None or self._fft_size != n:
            self._fft_size = n
            self._buffer = np.full((self._max_rows, n), -100.0, dtype=np.float32)
            self._row_index = 0

        # Satırı yaz
        self._buffer[self._row_index % self._max_rows] = fft_db
        self._row_index += 1

        # Dinamik seviye
        valid = self._buffer[self._buffer > -99]
        if len(valid) > 0:
            self._level_min = float(np.percentile(valid, 5))
            self._level_max = float(np.percentile(valid, 98))

        # Image güncelle — en son max_rows satırı göster
        total = min(self._row_index, self._max_rows)
        if self._row_index <= self._max_rows:
            display = self._buffer[:total]
        else:
            start = self._row_index % self._max_rows
            display = np.roll(self._buffer, -start, axis=0)

        self._image.setImage(
            display.T,
            levels=(self._level_min, self._level_max),
        )

        # Frekans ekseni ayarla (MHz)
        freq_min = (center_freq - sample_rate / 2) / 1e6
        freq_max = (center_freq + sample_rate / 2) / 1e6
        self._image.setRect(pg.QtCore.QRectF(freq_min, 0, freq_max - freq_min, total))

    def reset(self) -> None:
        """Waterfall'ı sıfırla."""
        self._buffer = None
        self._row_index = 0
        self._image.clear()
