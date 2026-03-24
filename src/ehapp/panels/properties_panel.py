"""
PropertiesPanel — Seçili node'un ayarlarını düzenleyen panel.

Node'a çift tıklanınca veya seçilince açılır/güncellenir.
config_schema'ya göre dinamik form oluşturur.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QScrollArea, QFrame, QPushButton, QFormLayout,
    QCheckBox, QFileDialog
)

from ehapp.theme.tokens import COLORS, FONTS, SIZES
from ehapp.strings.tr import PROPERTIES_TITLE
from ehcore.contracts import NodeDescriptor


class PropertiesPanel(QWidget):
    """Seçili node'un config'ini düzenleyen panel."""

    config_changed = Signal(str, dict)  # (instance_id, new_config)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(SIZES["properties_width"])

        self._current_node_id: str | None = None
        self._current_descriptor: NodeDescriptor | None = None
        self._widgets: dict[str, QWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Başlık ve Kapatma Butonu
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel(PROPERTIES_TITLE)
        self._title.setStyleSheet(
            f"color: {COLORS['text_accent']}; "
            f"font-weight: {FONTS['weight_bold']}; "
            f"font-size: {FONTS['size_md']}px; "
            f"padding: 4px;"
        )
        header_layout.addWidget(self._title)

        header_layout.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['text_accent']}; font-weight: bold; border: none; font-size: 16px; }}"
            f"QPushButton:hover {{ color: {COLORS['accent_primary']}; }}"
        )
        self._close_btn.clicked.connect(self.hide)
        header_layout.addWidget(self._close_btn)

        layout.addLayout(header_layout)

        # Node adı
        self._node_label = QLabel("")
        self._node_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 2px 4px;")
        layout.addWidget(self._node_label)

        # Scroll alan
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._form_container = QWidget()
        self._form_layout = QFormLayout(self._form_container)
        self._form_layout.setContentsMargins(4, 4, 4, 4)
        self._form_layout.setSpacing(6)
        scroll.setWidget(self._form_container)
        layout.addWidget(scroll, 1)

        # Uygula butonu
        self._apply_btn = QPushButton("Uygula")
        self._apply_btn.setStyleSheet(
            f"background-color: {COLORS['accent_primary']}; "
            f"color: {COLORS['bg_primary']}; "
            f"font-weight: {FONTS['weight_bold']}; "
            f"border-radius: {SIZES['radius_md']}px; "
            f"padding: 6px;"
        )
        self._apply_btn.clicked.connect(self._apply_config)
        layout.addWidget(self._apply_btn)

        self._clear_form()

    def show_node(self, instance_id: str, descriptor: NodeDescriptor, config: dict) -> None:
        """Node ayarlarını göster."""
        self._current_node_id = instance_id
        self._current_descriptor = descriptor
        self._node_label.setText(f"📦 {descriptor.display_name}")

        self._clear_form()
        self._build_form(descriptor.config_schema, config)
        self.show()

    def clear_selection(self) -> None:
        """Seçim temizle."""
        self._current_node_id = None
        self._current_descriptor = None
        self._node_label.setText("")
        self._clear_form()

    def _clear_form(self) -> None:
        """Formu temizle."""
        while self._form_layout.count():
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()

    def _build_form(self, schema: dict, config: dict) -> None:
        """config_schema'dan dinamik form oluştur."""
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
                widget.addItems([str(o) for o in options])
                if current is not None:
                    idx = widget.findText(str(current))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)

            elif field_type == "float":
                widget = QDoubleSpinBox()
                widget.setRange(-1e12, 1e12)
                widget.setDecimals(2)
                widget.setValue(float(current) if current else 0.0)

            elif field_type == "int":
                widget = QSpinBox()
                widget.setRange(-2**30, 2**30)
                widget.setValue(int(current) if current else 0)

            elif field_type == "bool":
                widget = QCheckBox()
                if current is not None:
                    widget.setChecked(bool(current))
                elif default is not None:
                    widget.setChecked(bool(default))

            elif field_type == "file":
                widget = QWidget()
                h_layout = QHBoxLayout(widget)
                h_layout.setContentsMargins(0, 0, 0, 0)
                
                line_edit = QLineEdit()
                line_edit.setText(str(current) if current else "")
                
                btn = QPushButton("Gözat...")
                # btn.clicked.connect(...) closure issues in loop, so we bind line_edit
                btn.clicked.connect(lambda _, le=line_edit: le.setText(
                    QFileDialog.getOpenFileName(widget, "Dosya Seç", "", "All Files (*)")[0] or le.text()
                ))
                
                h_layout.addWidget(line_edit)
                h_layout.addWidget(btn)
                widget.line_edit = line_edit # referans tutalım

            else:  # 'str' vs.
                widget = QLineEdit()
                widget.setText(str(current) if current else "")

            self._widgets[key] = widget
            self._form_layout.addRow(label_text + ":", widget)

    def _apply_config(self) -> None:
        """Formdaki değerleri config'e uygula."""
        if not self._current_node_id or not self._current_descriptor:
            return

        config = {}
        schema = self._current_descriptor.config_schema

        for key, widget in self._widgets.items():
            spec = schema.get(key, {})
            field_type = spec.get("type", "str") if isinstance(spec, dict) else "str"

            if isinstance(widget, QComboBox):
                val = widget.currentText()
                if field_type == "int":
                    val = int(val)
                elif field_type == "float":
                    val = float(val)
                config[key] = val
            elif isinstance(widget, QDoubleSpinBox):
                config[key] = widget.value()
            elif isinstance(widget, QSpinBox):
                config[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                config[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                config[key] = widget.text()
            elif hasattr(widget, "line_edit"):  # dosya seçici container widget
                config[key] = widget.line_edit.text()

        self.config_changed.emit(self._current_node_id, config)
