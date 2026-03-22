"""
DetectionsTable — Tespit sonuçları tablo görünümü.

Satır seçilince spektrum marker'ı güncellenebilir.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel,
)

from ehapp.theme.tokens import COLORS, FONTS
from ehapp.strings.tr import PLOT_DETECTIONS


class DetectionsTable(QWidget):
    """Tespit sonuçları tablosu."""

    detection_selected = Signal(float)  # Seçilen tespitinin frekansı (MHz)

    HEADERS = ["Frekans (MHz)", "Güç (dB)", "BW (kHz)", "Tip", "Zaman"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(PLOT_DETECTIONS)
        title.setStyleSheet(
            f"color: {COLORS['text_accent']}; "
            f"font-weight: {FONTS['weight_bold']}; "
            f"padding: 4px 8px;"
        )
        layout.addWidget(title)

        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.currentCellChanged.connect(self._on_selection)
        layout.addWidget(self._table)

    def add_detection(
        self,
        freq_mhz: float,
        power_db: float,
        bw_khz: float = 0.0,
        sig_type: str = "-",
        timestamp: str = "",
    ) -> None:
        """Tespit ekle."""
        row = self._table.rowCount()
        self._table.insertRow(row)

        items = [
            f"{freq_mhz:.4f}",
            f"{power_db:.1f}",
            f"{bw_khz:.1f}",
            sig_type,
            timestamp,
        ]
        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, col, item)

    def clear_detections(self) -> None:
        """Tabloyu temizle."""
        self._table.setRowCount(0)

    def _on_selection(self, row: int, col: int, prev_row: int, prev_col: int) -> None:
        """Satır seçilince frekans bilgisini yayınla."""
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item:
            try:
                freq = float(item.text())
                self.detection_selected.emit(freq)
            except ValueError:
                pass
