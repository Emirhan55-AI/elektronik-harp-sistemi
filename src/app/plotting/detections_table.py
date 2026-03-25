"""Operator odakli kalici tespit tablosu."""

from __future__ import annotations

import time

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.strings import tr
from app.theme.tokens import COLORS, FONTS


class DetectionsTable(QWidget):
    """Onayli hedefleri kararlı satirlarla gosterir."""

    detection_selected = Signal(float)

    HEADERS = [
        tr.DETECTIONS_HEADER_ID,
        tr.DETECTIONS_HEADER_STATE,
        tr.DETECTIONS_HEADER_FREQ,
        tr.DETECTIONS_HEADER_POWER,
        tr.DETECTIONS_HEADER_SNR,
        tr.DETECTIONS_HEADER_BW,
        tr.DETECTIONS_HEADER_HIT,
        tr.DETECTIONS_HEADER_LAST_SEEN,
        tr.DETECTIONS_HEADER_DURATION,
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._row_by_target_id: dict[int, int] = {}
        self._selected_target_id: int | None = None
        self._frozen = False
        self._show_stale = True
        self._last_snapshot: tuple[np.ndarray, float, float, int] | None = None
        self._pending_snapshot: tuple[np.ndarray, float, float, int] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header_frame = QFrame()
        header_frame.setStyleSheet(
            f"background-color: {COLORS['bg_secondary']}; "
            f"border-bottom: 1px solid {COLORS['border_default']};"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel(tr.PLOT_DETECTIONS)
        title.setStyleSheet(
            f"color: {COLORS['text_accent']}; "
            f"font-weight: {FONTS['weight_bold']}; "
            f"font-size: {FONTS['size_md']}px;"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._show_stale_check = QCheckBox(tr.DETECTIONS_SHOW_STALE)
        self._show_stale_check.setChecked(True)
        self._show_stale_check.toggled.connect(self._on_show_stale_toggled)
        header_layout.addWidget(self._show_stale_check)

        self._freeze_btn = QPushButton(tr.DETECTIONS_FREEZE)
        self._freeze_btn.setCheckable(True)
        self._freeze_btn.toggled.connect(self._on_freeze_toggled)
        header_layout.addWidget(self._freeze_btn)

        self._count_label = QLabel(tr.DETECTIONS_COUNT_ACTIVE.format(count=0))
        self._count_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; "
            f"font-size: {FONTS['size_sm']}px;"
        )
        header_layout.addWidget(self._count_label)
        layout.addWidget(header_frame)

        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._table.currentCellChanged.connect(self._on_selection)
        layout.addWidget(self._table)

    def update_confirmed_targets(
        self,
        confirmed_array: np.ndarray,
        center_freq: float = 0.0,
        sample_rate: float = 1.0,
        fft_size: int = 0,
    ) -> None:
        self._last_snapshot = (
            confirmed_array.copy(),
            float(center_freq),
            float(sample_rate),
            int(fft_size),
        )
        if self._frozen:
            self._pending_snapshot = self._last_snapshot
            return

        self._apply_snapshot(confirmed_array, center_freq, sample_rate, fft_size)

    def clear_detections(self) -> None:
        self._freeze_btn.blockSignals(True)
        self._freeze_btn.setChecked(False)
        self._freeze_btn.setText(tr.DETECTIONS_FREEZE)
        self._freeze_btn.blockSignals(False)
        self._frozen = False
        self._table.clearSelection()
        self._table.setRowCount(0)
        self._row_by_target_id.clear()
        self._selected_target_id = None
        self._last_snapshot = None
        self._pending_snapshot = None
        self._count_label.setText(tr.DETECTIONS_COUNT_ACTIVE.format(count=0))

    def _apply_snapshot(
        self,
        confirmed_array: np.ndarray,
        center_freq: float,
        sample_rate: float,
        fft_size: int,
    ) -> None:
        selected_id = self._current_selected_target_id()
        now = time.time()

        visible_rows: list[tuple[int, str, list[str]]] = []
        active_count = 0
        stale_count = 0

        for row_data in confirmed_array:
            target_id = int(row_data["target_id"])
            state = str(row_data["state"]).strip() or "confirmed"
            if state == "confirmed":
                active_count += 1
            elif state == "stale":
                stale_count += 1

            if not self._show_stale and state != "confirmed":
                continue

            freq_norm = float(row_data["center_freq_normalized"])
            freq_hz = freq_norm * sample_rate + center_freq
            freq_mhz = freq_hz / 1e6
            power_db = float(row_data["power_db"])
            snr_db = float(row_data["snr_db"])
            bw_bins = int(row_data["bandwidth_bins"])
            bin_resolution_hz = (sample_rate / fft_size) if fft_size > 0 else 0.0
            bw_khz = (bw_bins * bin_resolution_hz) / 1e3
            hit_count = int(row_data["hit_count"])
            first_seen = float(row_data["first_seen"])
            last_seen = float(row_data["last_seen"])
            age_since_seen = max(0.0, now - last_seen)
            duration = max(0.0, now - first_seen)

            state_label = (
                tr.DETECTIONS_STATE_ACTIVE
                if state == "confirmed"
                else tr.DETECTIONS_STATE_STALE
            )
            visible_rows.append(
                (
                    target_id,
                    state,
                    [
                        f"#{target_id}",
                        state_label,
                        f"{freq_mhz:.4f}",
                        f"{power_db:.1f}",
                        f"{snr_db:.1f}",
                        f"{bw_khz:.1f}",
                        f"{hit_count}",
                        f"{age_since_seen:.1f}",
                        f"{duration:.1f}",
                    ],
                )
            )

        self._table.blockSignals(True)
        self._remove_missing_targets({target_id for target_id, _, _ in visible_rows})

        for target_id, state, items in visible_rows:
            row = self._ensure_row(target_id)
            self._set_row_items(row, items)
            self._apply_row_style(row, state, float(items[4]))

        self._table.blockSignals(False)

        count_text = tr.DETECTIONS_COUNT_ACTIVE.format(count=active_count)
        if stale_count > 0:
            count_text = tr.DETECTIONS_COUNT_ACTIVE_STALE.format(
                active=active_count,
                stale=stale_count,
            )
        self._count_label.setText(count_text)

        if selected_id is not None and selected_id in self._row_by_target_id:
            row = self._row_by_target_id[selected_id]
            self._table.setCurrentCell(row, 0)

    def _ensure_row(self, target_id: int) -> int:
        row = self._row_by_target_id.get(target_id)
        if row is not None:
            return row

        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_by_target_id[target_id] = row
        return row

    def _set_row_items(self, row: int, values: list[str]) -> None:
        for col, text in enumerate(values):
            item = self._table.item(row, col)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)
            item.setText(text)

    def _apply_row_style(self, row: int, state: str, snr_db: float) -> None:
        if state == "confirmed":
            row_background = QColor(COLORS["state_active_bg"])
            base_color = QColor(COLORS["text_primary"])
            status_color = QColor(COLORS["success"])
        else:
            row_background = QColor(COLORS["state_passive_bg"])
            base_color = QColor(COLORS["state_passive"])
            status_color = QColor(COLORS["warning"])

        snr_color = base_color
        if state == "confirmed":
            if snr_db >= 10:
                snr_color = QColor(COLORS["success"])
            elif snr_db >= 5:
                snr_color = QColor(COLORS["warning"])
            else:
                snr_color = QColor(COLORS["state_alarm"])

        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item is None:
                continue
            item.setBackground(row_background)
            if col == 1:
                item.setForeground(status_color)
            elif col == 4:
                item.setForeground(snr_color)
            else:
                item.setForeground(base_color)

    def _remove_missing_targets(self, visible_target_ids: set[int]) -> None:
        missing_ids = [
            target_id
            for target_id in self._row_by_target_id
            if target_id not in visible_target_ids
        ]
        for target_id in sorted(
            missing_ids,
            key=lambda tid: self._row_by_target_id[tid],
            reverse=True,
        ):
            row = self._row_by_target_id[target_id]
            self._table.removeRow(row)
        if missing_ids:
            self._rebuild_row_map()

    def _rebuild_row_map(self) -> None:
        self._row_by_target_id.clear()
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is None:
                continue
            target_id = self._parse_target_id(item.text())
            if target_id is not None:
                self._row_by_target_id[target_id] = row

    def _current_selected_target_id(self) -> int | None:
        item = self._table.item(self._table.currentRow(), 0)
        if item is None:
            return self._selected_target_id
        target_id = self._parse_target_id(item.text())
        if target_id is not None:
            self._selected_target_id = target_id
        return self._selected_target_id

    def _on_selection(self, row: int, _col: int, _prev_row: int, _prev_col: int) -> None:
        if row < 0:
            return

        id_item = self._table.item(row, 0)
        if id_item is not None:
            self._selected_target_id = self._parse_target_id(id_item.text())

        item = self._table.item(row, 2)
        if item is None:
            return
        try:
            self.detection_selected.emit(float(item.text()))
        except ValueError:
            return

    def _on_freeze_toggled(self, frozen: bool) -> None:
        self._frozen = frozen
        self._freeze_btn.setText(tr.DETECTIONS_LIVE if frozen else tr.DETECTIONS_FREEZE)
        if not frozen and self._pending_snapshot is not None:
            snapshot = self._pending_snapshot
            self._pending_snapshot = None
            self._apply_snapshot(*snapshot)

    def _on_show_stale_toggled(self, checked: bool) -> None:
        self._show_stale = checked
        if not self._frozen and self._last_snapshot is not None:
            self._apply_snapshot(*self._last_snapshot)

    @staticmethod
    def _parse_target_id(text: str) -> int | None:
        cleaned = text.strip().lstrip("#")
        if not cleaned:
            return None
        try:
            return int(cleaned)
        except ValueError:
            return None


