"""
IQPlot — I ve Q bileşenlerini ayrı çizgiler olarak gösteren zaman grafiği.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ehapp.theme.tokens import COLORS
from ehapp.strings.tr import PLOT_IQ, PLOT_TIME_LABEL, PLOT_AMPLITUDE_LABEL


class IQPlot(QWidget):
    """IQ / Zaman grafiği — I ve Q ayrı çizgiler."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOptions(antialias=True, background=COLORS["plot_bg"])

        self._plot_widget = pg.PlotWidget(title=PLOT_IQ)
        self._plot_widget.setLabel("bottom", PLOT_TIME_LABEL)
        self._plot_widget.setLabel("left", PLOT_AMPLITUDE_LABEL)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self._plot_widget.addLegend(offset=(-10, 10))
        self._plot_widget.getAxis("bottom").setPen(pg.mkPen(COLORS["text_secondary"]))
        self._plot_widget.getAxis("left").setPen(pg.mkPen(COLORS["text_secondary"]))
        layout.addWidget(self._plot_widget)

        # I ve Q çizgileri
        self._i_curve = self._plot_widget.plot(
            pen=pg.mkPen(COLORS["plot_line1"], width=1.2),
            name="I (Eş-fazlı)",
        )
        self._q_curve = self._plot_widget.plot(
            pen=pg.mkPen(COLORS["plot_line2"], width=1.2),
            name="Q (Dik-fazlı)",
        )

    def update_data(self, iq_data: np.ndarray) -> None:
        """IQ verisini güncelle."""
        n = len(iq_data)
        x = np.arange(n)

        self._i_curve.setData(x, np.real(iq_data))
        self._q_curve.setData(x, np.imag(iq_data))

    def reset(self) -> None:
        """Grafiği sıfırla."""
        self._i_curve.setData([], [])
        self._q_curve.setData([], [])
        self._plot_widget.autoRange()
