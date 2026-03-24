"""
VariablesPanel - proje seviyesinde global degisken yonetimi.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ehapp.strings import tr


class VariablesPanel(QWidget):
    """Global degiskenleri duzenleyen panel."""

    variables_applied = Signal(dict)

    HEADERS = [
        tr.VARIABLE_HEADER_NAME,
        tr.VARIABLE_HEADER_TYPE,
        tr.VARIABLE_HEADER_VALUE,
    ]
    TYPES = [
        tr.VARIABLE_TYPE_TEXT,
        tr.VARIABLE_TYPE_INT,
        tr.VARIABLE_TYPE_FLOAT,
        tr.VARIABLE_TYPE_BOOL,
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = QLabel(tr.VARIABLES_HINT)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        toolbar = QHBoxLayout()
        self._add_btn = QPushButton(tr.VARIABLES_ADD_ROW)
        self._add_btn.clicked.connect(self._add_row)
        toolbar.addWidget(self._add_btn)

        self._remove_btn = QPushButton(tr.VARIABLES_REMOVE_ROW)
        self._remove_btn.clicked.connect(self._remove_selected_row)
        toolbar.addWidget(self._remove_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._table = QTableWidget(0, len(self.HEADERS))
        self._table.setHorizontalHeaderLabels(self.HEADERS)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, 1)

        self._apply_btn = QPushButton(tr.VARIABLES_APPLY)
        self._apply_btn.setObjectName("PrimaryButton")
        self._apply_btn.clicked.connect(self._emit_variables)
        layout.addWidget(self._apply_btn)

    def set_variables(self, variables: dict[str, object]) -> None:
        self._table.setRowCount(0)
        for name, value in sorted(variables.items()):
            self._add_row(name=name, value=value)

    def _add_row(self, checked: bool = False, name: str = "", value: object = "") -> None:
        del checked
        row = self._table.rowCount()
        self._table.insertRow(row)

        name_item = QTableWidgetItem(str(name))
        self._table.setItem(row, 0, name_item)

        type_combo = QComboBox()
        type_combo.addItems(self.TYPES)
        type_combo.setCurrentText(self._infer_type_label(value))
        self._table.setCellWidget(row, 1, type_combo)

        value_item = QTableWidgetItem(self._format_value(value))
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._table.setItem(row, 2, value_item)

    def _remove_selected_row(self) -> None:
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)

    def _emit_variables(self) -> None:
        variables: dict[str, object] = {}
        for row in range(self._table.rowCount()):
            name_item = self._table.item(row, 0)
            value_item = self._table.item(row, 2)
            type_combo = self._table.cellWidget(row, 1)
            if name_item is None or value_item is None or type_combo is None:
                continue
            name = name_item.text().strip()
            if not name:
                continue
            variables[name] = self._parse_value(type_combo.currentText(), value_item.text().strip())
        self.variables_applied.emit(variables)

    @staticmethod
    def _infer_type_label(value: object) -> str:
        if isinstance(value, bool):
            return tr.VARIABLE_TYPE_BOOL
        if isinstance(value, int) and not isinstance(value, bool):
            return tr.VARIABLE_TYPE_INT
        if isinstance(value, float):
            return tr.VARIABLE_TYPE_FLOAT
        return tr.VARIABLE_TYPE_TEXT

    @staticmethod
    def _format_value(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _parse_value(type_label: str, raw: str) -> object:
        if type_label == tr.VARIABLE_TYPE_INT:
            return int(raw) if raw else 0
        if type_label == tr.VARIABLE_TYPE_FLOAT:
            return float(raw) if raw else 0.0
        if type_label == tr.VARIABLE_TYPE_BOOL:
            return raw.lower() in {"1", "true", "evet", "yes"}
        return raw
