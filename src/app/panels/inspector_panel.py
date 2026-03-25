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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.strings import tr
from app.theme.tokens import COLORS, FONTS, SIZES
from ehplatform.contracts import NodeDescriptor


class InspectorPanel(QWidget):
    """Secili blok icin config ve runtime bilgisini gosterir."""

    config_changed = Signal(str, dict)
    close_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("InspectorRoot")
        self.setMinimumWidth(SIZES["properties_width"] + 40)

        self._current_node_id: str | None = None
        self._current_descriptor: NodeDescriptor | None = None
        self._widgets: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

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
        self._close_btn.clicked.connect(self.close_requested.emit)
        header.addWidget(self._close_btn)
        layout.addLayout(header)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.currentChanged.connect(self._sync_title_with_tab)
        layout.addWidget(self._tabs)

        # -- Detaylar Sekmesi --
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(8, 8, 8, 8)
        details_layout.setSpacing(10)

        self._name_label = QLabel("")
        self._name_label.setStyleSheet(
            f"font-size: {FONTS['size_md']}px; font-weight: {FONTS['weight_bold']}; "
            f"color: {COLORS['text_accent']};"
        )
        details_layout.addWidget(self._name_label)

        self._description = QLabel("")
        self._description.setWordWrap(True)
        self._description.setStyleSheet(f"color: {COLORS['text_secondary']};")
        details_layout.addWidget(self._description)

        self._ports_label = QLabel("")
        self._ports_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        details_layout.addWidget(self._ports_label)

        runtime_card = QFrame()
        runtime_card.setObjectName("InspectorCard")
        runtime_layout = QFormLayout(runtime_card)
        runtime_layout.setContentsMargins(12, 12, 12, 12)
        runtime_layout.setSpacing(8)

        self._runtime_state = QLabel(tr.INSPECTOR_STATE_IDLE)
        self._runtime_frames = QLabel("0")
        self._runtime_drops = QLabel("0")
        self._runtime_latency = QLabel("0.0 ms")
        self._runtime_avg_latency = QLabel("0.0 ms")
        self._runtime_last_seen = QLabel("-")
        self._runtime_error = QLabel("-")
        self._runtime_error.setWordWrap(True)
        self._probe_summary = QLabel("-")
        self._probe_summary.setWordWrap(True)
        self._probe_history = QLabel("-")

        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_STATE, self._runtime_state)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_FRAMES, self._runtime_frames)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_DROPS, self._runtime_drops)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_LATENCY, self._runtime_latency)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_AVG_LATENCY, self._runtime_avg_latency)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_LAST_SEEN, self._runtime_last_seen)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_LAST_OUTPUT, self._probe_summary)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_PROBE_HISTORY, self._probe_history)
        runtime_layout.addRow(tr.INSPECTOR_RUNTIME_LAST_ERROR, self._runtime_error)
        
        details_layout.addWidget(runtime_card)
        details_layout.addStretch()
        self._tabs.addTab(details_widget, tr.INSPECTOR_TAB_DETAILS)

        # -- Ayarlar Sekmesi --
        self._form_tab = QWidget()
        settings_layout = QVBoxLayout(self._form_tab)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._form_container = QWidget()
        self._form_layout = QFormLayout(self._form_container)
        self._form_layout.setContentsMargins(4, 10, 4, 10)
        self._form_layout.setSpacing(12)
        scroll.setWidget(self._form_container)
        settings_layout.addWidget(scroll)

        self._apply_btn = QPushButton(tr.INSPECTOR_APPLY)
        self._apply_btn.setObjectName("PrimaryButton")
        self._apply_btn.setMinimumHeight(32)
        self._apply_btn.clicked.connect(self._apply_config)
        settings_layout.addWidget(self._apply_btn)
        
        self._tabs.addTab(self._form_tab, tr.INSPECTOR_TAB_PROPERTIES)

        self._clear_form()
        self.clear_selection()

    def show_node(
        self,
        instance_id: str,
        descriptor: NodeDescriptor,
        config: dict,
        runtime_info: dict | None = None,
    ) -> None:
        if self._current_node_id != instance_id:
            self._current_node_id = instance_id
            self._current_descriptor = descriptor
            self._rebuild_form(descriptor, config)
            self._tabs.setCurrentWidget(self._form_tab)
            self._sync_title_with_tab()

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
            f"{tr.INSPECTOR_LABEL_INPUTS}: {inputs}\n"
            f"{tr.INSPECTOR_LABEL_OUTPUTS}: {outputs}"
        )

        if runtime_info:
            self._update_runtime_ui(runtime_info)
        self.show()

    def _update_runtime_ui(self, info: dict) -> None:
        state = info.get("state", "idle")
        label = {
            "idle": tr.INSPECTOR_STATE_IDLE,
            "running": tr.INSPECTOR_STATE_RUNNING,
            "warning": tr.INSPECTOR_STATE_WARNING,
            "stale": tr.INSPECTOR_STATE_STALE,
            "error": tr.INSPECTOR_STATE_ERROR,
        }.get(state, state)
        self._runtime_state.setText(label)
        
        color = COLORS["text_secondary"]
        if state == "running": color = COLORS["success"]
        elif state == "warning": color = COLORS["warning"]
        elif state == "error": color = COLORS["error"]
        self._runtime_state.setStyleSheet(f"color: {color}; font-weight: bold;")

        metrics = info.get("metrics")
        if metrics:
            self._runtime_frames.setText(str(getattr(metrics, "frame_count", 0)))
            self._runtime_drops.setText(str(getattr(metrics, "dropped_frames", 0)))
            self._runtime_latency.setText(
                f"{float(getattr(metrics, 'last_process_duration_ms', 0.0)):.1f} ms"
            )
            self._runtime_avg_latency.setText(
                f"{float(getattr(metrics, 'average_process_duration_ms', 0.0)):.1f} ms"
            )
            
            if metrics.last_tick_timestamp > 0:
                age = time.time() - metrics.last_tick_timestamp
                self._runtime_last_seen.setText(tr.INSPECTOR_ELAPSED.format(age=age))
            else:
                self._runtime_last_seen.setText("-")

        runtime_error = info.get("last_error") or (getattr(metrics, "last_error", "") if metrics else "")
        self._runtime_error.setText(runtime_error or "-")
        self._probe_summary.setText(info.get("probe_summary") or "-")
        self._probe_history.setText(info.get("probe_history_summary") or "-")

    def clear_selection(self) -> None:
        self._current_node_id = None
        self._current_descriptor = None
        self._sync_title_with_tab()
        self._name_label.setText(tr.INSPECTOR_TITLE)
        self._description.setText(tr.INSPECTOR_SELECT_HINT)
        self._ports_label.setText("")
        self._runtime_state.setText("-")
        self._clear_form()

    def _clear_form(self) -> None:
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()

    def _rebuild_form(self, descriptor: NodeDescriptor, config: dict) -> None:
        self._clear_form()
        for key, field in descriptor.config_schema.items():
            field_type = field.get("type", "str")
            label = field.get("label", key)
            default = field.get("default")
            current = config.get(key, default)

            widget: QWidget
            if field_type == "choice":
                widget = QComboBox()
                options = field.get("options", [])
                widget.addItems(options)
                if current in options:
                    widget.setCurrentText(current)
            elif field_type == "float":
                widget = QDoubleSpinBox()
                widget.setRange(-1e12, 1e12)
                widget.setDecimals(3)
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
                
                # Capture lambda fix: Qt passed 'checked' bool as first argument
                def browse_requested(le=line_edit):
                    try:
                        path, _ = QFileDialog.getOpenFileName(
                            self,
                            tr.INSPECTOR_FILE_PICKER_TITLE,
                            "",
                            tr.INSPECTOR_FILE_PICKER_FILTER,
                        )
                        if path:
                            le.setText(path)
                    except RuntimeError:
                        pass

                btn.clicked.connect(lambda: browse_requested())
                h_layout.addWidget(line_edit)
                h_layout.addWidget(btn)
                widget.line_edit = line_edit
            else:
                field_widget = QLineEdit()
                field_widget.setText(str(current) if current else "")
                widget = field_widget

            self._widgets[key] = widget
            self._form_layout.addRow(label, widget)

    def _apply_config(self) -> None:
        if not self._current_node_id or not self._current_descriptor:
            return

        new_config = {}
        for key, widget in self._widgets.items():
            if isinstance(widget, QLineEdit):
                new_config[key] = widget.text()
            elif isinstance(widget, QDoubleSpinBox):
                new_config[key] = widget.value()
            elif isinstance(widget, QSpinBox):
                new_config[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                new_config[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                new_config[key] = widget.currentText()
            elif hasattr(widget, "line_edit"):
                new_config[key] = widget.line_edit.text()

        self.config_changed.emit(self._current_node_id, new_config)

    def _sync_title_with_tab(self) -> None:
        if not hasattr(self, "_form_tab"):
            return
        current_widget = self._tabs.currentWidget()
        if current_widget is self._form_tab:
            self._title.setText(tr.INSPECTOR_TAB_PROPERTIES)
        else:
            self._title.setText(tr.INSPECTOR_TAB_DETAILS)

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


