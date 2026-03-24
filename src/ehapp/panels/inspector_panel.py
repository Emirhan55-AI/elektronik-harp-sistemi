"""
InspectorPanel - secili blok icin config, aciklama ve runtime paneli.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ehapp.strings import tr
from ehapp.theme.tokens import COLORS, FONTS, SIZES
from ehcore.contracts import NodeDescriptor


class InspectorPanel(QWidget):
    """Secili blok icin config ve runtime bilgisini gosterir."""

    config_changed = Signal(str, dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(SIZES["properties_width"] + 28)

        self._current_node_id: str | None = None
        self._current_descriptor: NodeDescriptor | None = None
        self._widgets: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._title = QLabel(tr.INSPECTOR_TITLE)
        self._title.setStyleSheet(
            f"color: {COLORS['text_accent']};"
            f" font-size: {FONTS['size_lg']}px;"
            f" font-weight: {FONTS['weight_bold']};"
        )
        header.addWidget(self._title)
        header.addStretch()

        self._close_btn = QPushButton("x")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setObjectName("IconButton")
        self._close_btn.setToolTip(tr.INSPECTOR_CLOSE_TOOLTIP)
        self._close_btn.clicked.connect(self.hide)
        header.addWidget(self._close_btn)
        layout.addLayout(header)

        self._name_label = QLabel("")
        self._name_label.setStyleSheet(
            f"font-size: {FONTS['size_md']}px; font-weight: {FONTS['weight_bold']};"
        )
        layout.addWidget(self._name_label)

        self._description = QLabel("")
        self._description.setWordWrap(True)
        self._description.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self._description)

        self._ports_label = QLabel("")
        self._ports_label.setWordWrap(True)
        self._ports_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(self._ports_label)

        runtime_card = QFrame()
        runtime_card.setObjectName("InspectorCard")
        runtime_layout = QFormLayout(runtime_card)
        runtime_layout.setContentsMargins(10, 10, 10, 10)
        runtime_layout.setSpacing(6)

        self._runtime_state = QLabel(tr.INSPECTOR_STATE_IDLE)
        self._runtime_frames = QLabel("0")
        self._runtime_drops = QLabel("0")
        self._runtime_latency = QLabel("0.0 ms")
        self._runtime_avg_latency = QLabel("0.0 ms")
        self._runtime_last_seen = QLabel(tr.COMMON_PLACEHOLDER)
        self._runtime_error = QLabel(tr.COMMON_PLACEHOLDER)
        self._runtime_error.setWordWrap(True)
        self._probe_summary = QLabel(tr.COMMON_PLACEHOLDER)
        self._probe_summary.setWordWrap(True)
        self._probe_history = QLabel(tr.COMMON_PLACEHOLDER)
        self._probe_history.setWordWrap(True)

        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_STATE, self._runtime_state)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_FRAMES, self._runtime_frames)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_DROPS, self._runtime_drops)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_LATENCY, self._runtime_latency)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_AVG_LATENCY, self._runtime_avg_latency)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_LAST_SEEN, self._runtime_last_seen)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_LAST_OUTPUT, self._probe_summary)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_PROBE_HISTORY, self._probe_history)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_LAST_ERROR, self._runtime_error)
        layout.addWidget(runtime_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._form_container = QWidget()
        self._form_layout = QFormLayout(self._form_container)
        self._form_layout.setContentsMargins(4, 4, 4, 4)
        self._form_layout.setSpacing(8)
        scroll.setWidget(self._form_container)
        layout.addWidget(scroll, 1)

        self._apply_btn = QPushButton(tr.INSPECTOR_APPLY)
        self._apply_btn.setObjectName("PrimaryButton")
        self._apply_btn.clicked.connect(self._apply_config)
        layout.addWidget(self._apply_btn)

        self._clear_form()
        self.clear_selection()

    def show_node(
        self,
        instance_id: str,
        descriptor: NodeDescriptor,
        config: dict,
        runtime_info: dict | None = None,
    ) -> None:
        self._current_node_id = instance_id
        self._current_descriptor = descriptor
        self._name_label.setText(descriptor.display_name)
        self._description.setText(descriptor.description or tr.INSPECTOR_DESCRIPTION_MISSING)

        inputs = ", ".join(
            f"{port.display_name} ({port.port_type.display_name()})"
            for port in descriptor.input_ports
        ) or tr.INSPECTOR_PORT_NONE
        outputs = ", ".join(
            f"{port.display_name} ({port.port_type.display_name()})"
            for port in descriptor.output_ports
        ) or tr.INSPECTOR_PORT_NONE
        self._ports_label.setText(
            f"{tr.INSPECTOR_PORT_INPUTS.format(value=inputs)}\n"
            f"{tr.INSPECTOR_PORT_OUTPUTS.format(value=outputs)}"
        )

        self._clear_form()
        self._build_form(descriptor.config_schema, config)
        self.update_runtime_info(runtime_info or {})
        self.show()

    def update_runtime_info(self, runtime_info: dict | None) -> None:
        info = runtime_info or {}
        metrics = info.get("metrics")
        state = self._translate_state(str(info.get("state", "idle")))
        last_error = str(info.get("last_error", "")).strip() or tr.COMMON_PLACEHOLDER
        probe_snapshot = info.get("probe_snapshot") or []
        probe_history = info.get("probe_history") or []

        self._runtime_state.setText(state)
        if metrics is None:
            self._runtime_frames.setText("0")
            self._runtime_drops.setText("0")
            self._runtime_latency.setText("0.0 ms")
            self._runtime_avg_latency.setText("0.0 ms")
            self._runtime_last_seen.setText(tr.COMMON_PLACEHOLDER)
        else:
            self._runtime_frames.setText(str(metrics.frame_count))
            self._runtime_drops.setText(str(metrics.dropped_frames))
            self._runtime_latency.setText(f"{metrics.last_process_duration_ms:.1f} ms")
            self._runtime_avg_latency.setText(f"{metrics.average_process_duration_ms:.1f} ms")
            if metrics.last_tick_timestamp > 0:
                self._runtime_last_seen.setText(self._format_elapsed(metrics.last_tick_timestamp))
            else:
                self._runtime_last_seen.setText(tr.COMMON_PLACEHOLDER)

        if probe_snapshot:
            self._probe_summary.setText(
                "\n".join(
                    f"{item['port_name']}: {item['data_type']} - {item['payload_summary']}"
                    for item in probe_snapshot[:3]
                )
            )
        else:
            self._probe_summary.setText(tr.COMMON_PLACEHOLDER)

        if probe_history:
            self._probe_history.setText(
                "\n".join(self._format_probe_history_item(item) for item in probe_history[:5])
            )
        else:
            self._probe_history.setText(tr.COMMON_PLACEHOLDER)

        self._runtime_error.setText(last_error)

    def clear_selection(self) -> None:
        self._current_node_id = None
        self._current_descriptor = None
        self._name_label.setText("")
        self._description.setText("")
        self._ports_label.setText("")
        self.update_runtime_info({})
        self._clear_form()

    def _clear_form(self) -> None:
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()

    def _build_form(self, schema: dict, config: dict) -> None:
        for key, spec in schema.items():
            if not isinstance(spec, dict):
                continue

            label_text = str(spec.get("label", key))
            field_type = spec.get("type", "str")
            default = spec.get("default")
            current = config.get(key, default)
            options = spec.get("options")

            widget: QWidget
            if options and isinstance(options, list):
                widget = QComboBox()
                widget.addItems([str(option) for option in options])
                if current is not None:
                    idx = widget.findText(str(current))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
            elif field_type == "float":
                widget = QDoubleSpinBox()
                widget.setRange(-1e12, 1e12)
                widget.setDecimals(2)
                widget.setValue(float(current) if current not in (None, "") else 0.0)
            elif field_type == "int":
                widget = QSpinBox()
                widget.setRange(-2**30, 2**30)
                widget.setValue(int(current) if current not in (None, "") else 0)
            elif field_type == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(current if current is not None else default))
            elif field_type == "file":
                widget = QWidget()
                h_layout = QHBoxLayout(widget)
                h_layout.setContentsMargins(0, 0, 0, 0)
                line_edit = QLineEdit()
                line_edit.setText(str(current) if current else "")
                btn = QPushButton(tr.INSPECTOR_FILE_BROWSE)
                btn.clicked.connect(
                    lambda _, le=line_edit: le.setText(
                        QFileDialog.getOpenFileName(
                            widget,
                            tr.INSPECTOR_FILE_PICKER_TITLE,
                            "",
                            tr.INSPECTOR_FILE_PICKER_FILTER,
                        )[0]
                        or le.text()
                    )
                )
                h_layout.addWidget(line_edit)
                h_layout.addWidget(btn)
                widget.line_edit = line_edit
            else:
                widget = QLineEdit()
                widget.setText(str(current) if current else "")

            self._widgets[key] = widget
            self._form_layout.addRow(label_text + ":", widget)

    def _apply_config(self) -> None:
        if not self._current_node_id or not self._current_descriptor:
            return

        config = {}
        schema = self._current_descriptor.config_schema
        for key, widget in self._widgets.items():
            spec = schema.get(key, {})
            field_type = spec.get("type", "str") if isinstance(spec, dict) else "str"

            if isinstance(widget, QComboBox):
                value = widget.currentText()
                if field_type == "int":
                    value = int(value)
                elif field_type == "float":
                    value = float(value)
                config[key] = value
            elif isinstance(widget, QDoubleSpinBox):
                config[key] = widget.value()
            elif isinstance(widget, QSpinBox):
                config[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                config[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                config[key] = widget.text()
            elif hasattr(widget, "line_edit"):
                config[key] = widget.line_edit.text()

        self.config_changed.emit(self._current_node_id, config)

    @staticmethod
    def _format_elapsed(last_timestamp: float) -> str:
        age = max(0.0, time.time() - last_timestamp)
        return tr.INSPECTOR_ELAPSED.format(age=age)

    @staticmethod
    def _format_probe_history_item(item: dict) -> str:
        port_name = str(item.get("port_name", tr.COMMON_PLACEHOLDER))
        payload_summary = str(item.get("payload_summary", tr.COMMON_PLACEHOLDER))
        metadata_summary = str(item.get("metadata_summary", tr.COMMON_PLACEHOLDER))
        timestamp = float(item.get("timestamp", 0.0))
        age = max(0.0, time.time() - timestamp) if timestamp > 0 else 0.0
        center_freq = float(item.get("center_freq", 0.0))
        freq_label = (
            f"{center_freq / 1e6:.3f} MHz"
            if center_freq > 0
            else tr.COMMON_PLACEHOLDER
        )
        base = f"{port_name} - {freq_label} - {age:.1f} sn - {payload_summary}"
        if metadata_summary and metadata_summary != tr.COMMON_PLACEHOLDER:
            return f"{base} - {metadata_summary}"
        return base

    @staticmethod
    def _translate_state(state: str) -> str:
        return {
            "idle": tr.INSPECTOR_STATE_IDLE,
            "running": tr.INSPECTOR_STATE_RUNNING,
            "warning": tr.INSPECTOR_STATE_WARNING,
            "stale": tr.INSPECTOR_STATE_STALE,
            "error": tr.INSPECTOR_STATE_ERROR,
        }.get(state, state)
