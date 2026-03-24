"""
DetectionsTable — Tespit sonuçları tablo görünümü.

İki modda çalışır:
  1. Ham CFAR tespitleri (cfar_adapter çıkışı)
  2. Onaylı hedefler (stability_adapter çıkışı) — asıl hakem verimiz

Satır seçilince spektrum marker'ı güncellenebilir.
"""

from __future__ import annotations

import time

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QHBoxLayout, QFrame,
)

from ehapp.theme.tokens import COLORS, FONTS
from ehapp.strings.tr import PLOT_DETECTIONS


class DetectionsTable(QWidget):
    """Onaylı tespit sonuçları tablosu."""

    detection_selected = Signal(float)  # Seçilen tespitinin frekansı (MHz)

    HEADERS = [
        "ID",
        "Merkez Frekans (MHz)",
        "Güç (dB)",
        "SNR (dB)",
        "BW (kHz)",
        "Hit",
        "Süre (s)",
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Üst bilgi çubuğu
        header_frame = QFrame()
        header_frame.setStyleSheet(
            f"background-color: {COLORS['bg_secondary']}; "
            f"border-bottom: 1px solid {COLORS['border_default']};"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel(f"🎯  {PLOT_DETECTIONS}")
        title.setStyleSheet(
            f"color: {COLORS['text_accent']}; "
            f"font-weight: {FONTS['weight_bold']}; "
            f"font-size: {FONTS['size_md']}px;"
        )
        header_layout.addWidget(title)

        self._count_label = QLabel("0 hedef")
        self._count_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; "
            f"font-size: {FONTS['size_sm']}px;"
        )
        header_layout.addStretch()
        header_layout.addWidget(self._count_label)
        layout.addWidget(header_frame)

        # Tablo
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

    def update_confirmed_targets(
        self,
        confirmed_array: np.ndarray,
        center_freq: float = 0.0,
        sample_rate: float = 1.0,
        fft_size: int = 0,
    ) -> None:
        """
        Onaylı hedef tablosunu tamamen güncelle.

        Args:
            confirmed_array: Stability adapter çıkışı (structured array).
            center_freq: Merkez frekans (Hz).
            sample_rate: Örnekleme hızı (Hz).
        """
        self._table.setRowCount(0)

        if confirmed_array.size == 0:
            self._count_label.setText("0 hedef")
            return

        now = time.time()

        for row_data in confirmed_array:
            row = self._table.rowCount()
            self._table.insertRow(row)

            target_id = int(row_data["target_id"])
            freq_norm = float(row_data["center_freq_normalized"])
            freq_hz = freq_norm * sample_rate + center_freq
            freq_mhz = freq_hz / 1e6
            power_db = float(row_data["power_db"])
            snr_db = float(row_data["snr_db"])
            bw_bins = int(row_data["bandwidth_bins"])
            bin_resolution_hz = (sample_rate / fft_size) if fft_size > 0 else 0.0
            bw_hz = bw_bins * bin_resolution_hz
            bw_khz = bw_hz / 1e3
            hit_count = int(row_data["hit_count"])
            first_seen = float(row_data["first_seen"])
            duration = now - first_seen

            items = [
                f"#{target_id}",
                f"{freq_mhz:.4f}",
                f"{power_db:.1f}",
                f"{snr_db:.1f}",
                f"{bw_khz:.1f}",
                f"{hit_count}",
                f"{duration:.1f}",
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # SNR'ye göre renklendirme
                if col == 3:  # SNR sütunu
                    if snr_db >= 10:
                        item.setForeground(QColor(COLORS["success"]))
                    elif snr_db >= 5:
                        item.setForeground(QColor(COLORS["warning"]))
                    else:
                        item.setForeground(QColor(COLORS["text_primary"]))

                self._table.setItem(row, col, item)

        count = self._table.rowCount()
        self._count_label.setText(f"{count} hedef")

    def clear_detections(self) -> None:
        """Tabloyu temizle."""
        self._table.setRowCount(0)
        self._count_label.setText("0 hedef")

    def _on_selection(self, row: int, col: int, prev_row: int, prev_col: int) -> None:
        """Satır seçilince frekans bilgisini yayınla."""
        if row < 0:
            return
        item = self._table.item(row, 1)  # Frekans sütunu
        if item:
            try:
                freq = float(item.text())
                self.detection_selected.emit(freq)
            except ValueError:
                pass
