"""
NodeItem - QGraphicsItem tabanli node kutusu.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsTextItem,
)

from ehapp.strings import tr
from ehapp.theme.tokens import COLORS, FONTS, SIZES
from ehcore.contracts import NodeDescriptor

from .port_item import PortItem


class NodeItem(QGraphicsItem):
    """Pipeline canvas uzerindeki tek bir node kutusu."""

    def __init__(
        self,
        instance_id: str,
        descriptor: NodeDescriptor,
        config: dict | None = None,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)

        self.instance_id = instance_id
        self.descriptor = descriptor
        self.config = config or descriptor.default_config()

        self._min_width = SIZES["node_min_width"]
        self._header_h = SIZES["node_header_h"]
        self._port_spacing = SIZES["node_port_spacing"]
        self._border_w = SIZES["node_border"]
        self._radius = SIZES["radius_lg"]

        self._input_ports: list[PortItem] = []
        self._output_ports: list[PortItem] = []
        self._visible_input_defs = [port for port in descriptor.input_ports if port.visible]
        self._visible_output_defs = [port for port in descriptor.output_ports if port.visible]

        port_rows = max(len(self._visible_input_defs), len(self._visible_output_defs), 1)
        self._body_h = port_rows * self._port_spacing + 12
        self._width = self._min_width
        self._height = self._header_h + self._body_h

        self._bg_color = QColor(COLORS["node_bg"])
        self._header_color = QColor(COLORS["node_header"])
        self._border_color = QColor(COLORS["border_default"])
        self._selected_border = QColor(COLORS["node_selected"])
        self._text_color = QColor(COLORS["text_primary"])

        self._state = "idle"
        self._validation_severity: str | None = None
        self._validation_messages: list[str] = []

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

        self._glow_effect = QGraphicsDropShadowEffect()
        self._glow_effect.setBlurRadius(25)
        self._glow_effect.setColor(QColor(COLORS["success"]))
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setEnabled(False)
        self.setGraphicsEffect(self._glow_effect)

        self._title_item = QGraphicsTextItem(descriptor.display_name, self)
        self._title_item.setDefaultTextColor(self._text_color)
        title_font = QFont(FONTS["family"], FONTS["size_sm"])
        title_font.setWeight(QFont.Weight.Medium)
        self._title_item.setFont(title_font)
        self._title_item.setPos(8, 3)

        tooltip = self._build_tooltip()
        self.setToolTip(tooltip)
        self._title_item.setToolTip(tooltip)

        self._validation_item = QGraphicsTextItem("", self)
        self._validation_item.setDefaultTextColor(QColor(COLORS["warning"]))
        validation_font = QFont(FONTS["family"], max(8, FONTS["size_sm"] - 1))
        self._validation_item.setFont(validation_font)
        self._validation_item.setPos(8, self._height + 4)
        self._validation_item.hide()

        title_width = self._title_item.boundingRect().width() + 20
        self._width = max(self._min_width, title_width)

        self._create_ports()

    def _create_ports(self) -> None:
        for index, port_def in enumerate(self._visible_input_defs):
            port = PortItem(port_def, is_output=False, parent=self)
            port.setPos(0, self._header_h + 12 + index * self._port_spacing)
            self._input_ports.append(port)

        for index, port_def in enumerate(self._visible_output_defs):
            port = PortItem(port_def, is_output=True, parent=self)
            port.setPos(self._width, self._header_h + 12 + index * self._port_spacing)
            self._output_ports.append(port)

    def _build_tooltip(self) -> str:
        lines: list[str] = []
        if self.descriptor.description:
            lines.append(self.descriptor.description)

        if self._visible_input_defs:
            inputs = ", ".join(port.display_name for port in self._visible_input_defs)
            lines.append(tr.NODE_TOOLTIP_INPUTS.format(value=inputs))
        else:
            lines.append(tr.NODE_TOOLTIP_INPUTS.format(value=tr.NODE_TOOLTIP_NONE))

        if self._visible_output_defs:
            outputs = ", ".join(port.display_name for port in self._visible_output_defs)
            lines.append(tr.NODE_TOOLTIP_OUTPUTS.format(value=outputs))
        else:
            lines.append(tr.NODE_TOOLTIP_OUTPUTS.format(value=tr.NODE_TOOLTIP_NONE))

        return "\n".join(lines)

    @property
    def input_ports(self) -> list[PortItem]:
        return self._input_ports

    @property
    def output_ports(self) -> list[PortItem]:
        return self._output_ports

    def get_port(self, name: str) -> PortItem | None:
        for port in self._input_ports + self._output_ports:
            if port.port_def.name == name:
                return port
        return None

    def set_state(self, state: str) -> None:
        self._state = state
        if state == "running":
            self._glow_effect.setEnabled(True)
            self._glow_effect.setColor(QColor(COLORS["success"]))
        elif state == "warning":
            self._glow_effect.setEnabled(True)
            self._glow_effect.setColor(QColor(COLORS["warning"]))
        elif state == "stale":
            self._glow_effect.setEnabled(True)
            self._glow_effect.setColor(QColor(COLORS["info"]))
        elif state == "error":
            self._glow_effect.setEnabled(True)
            self._glow_effect.setColor(QColor(COLORS["node_error"]))
        else:
            self._glow_effect.setEnabled(False)
        self.update()

    def set_validation_messages(self, messages: list[str], severity: str | None = None) -> None:
        self._validation_messages = messages
        self._validation_severity = severity
        if not messages:
            self._validation_item.hide()
            self.update()
            return

        self._validation_item.setPlainText(messages[0])
        color_key = "error" if severity == "error" else "warning"
        self._validation_item.setDefaultTextColor(QColor(COLORS[color_key]))
        self._validation_item.setPos(8, self._height + 4)
        self._validation_item.show()
        self.update()

    def boundingRect(self) -> QRectF:
        margin = self._border_w
        return QRectF(-margin, -margin, self._width + 2 * margin, self._height + 2 * margin)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self._width, self._height)
        header_rect = QRectF(0, 0, self._width, self._header_h)

        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(rect.adjusted(2, 2, 2, 2), self._radius, self._radius)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 60))

        body_path = QPainterPath()
        body_path.addRoundedRect(rect, self._radius, self._radius)
        painter.fillPath(body_path, QBrush(self._bg_color))

        gradient = QLinearGradient(0, 0, 0, self._header_h)
        gradient.setColorAt(0, self._header_color)
        gradient.setColorAt(1, self._bg_color)

        header_path = QPainterPath()
        header_path.addRoundedRect(header_rect, self._radius, self._radius)
        header_path.addRect(QRectF(0, self._header_h - self._radius, self._width, self._radius))
        painter.fillPath(header_path, QBrush(gradient))

        border_color = self._border_color
        border_width = self._border_w

        if self.isSelected():
            border_color = self._selected_border
            border_width = 2.5
        elif self._validation_severity == "error":
            border_color = QColor(COLORS["error"])
        elif self._validation_severity == "warning":
            border_color = QColor(COLORS["warning"])
        elif self._state == "running":
            border_color = QColor(COLORS["node_running"])
        elif self._state == "warning":
            border_color = QColor(COLORS["warning"])
        elif self._state == "stale":
            border_color = QColor(COLORS["info"])
        elif self._state == "error":
            border_color = QColor(COLORS["node_error"])

        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(rect, self._radius, self._radius)

        if self._state != "idle":
            if self._state == "running":
                indicator_color = QColor(COLORS["node_running"])
            elif self._state == "warning":
                indicator_color = QColor(COLORS["warning"])
            elif self._state == "stale":
                indicator_color = QColor(COLORS["info"])
            else:
                indicator_color = QColor(COLORS["node_error"])

            painter.setBrush(QBrush(indicator_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(self._width - 12, 10), 4, 4)

        painter.setPen(QPen(QColor(COLORS["border_default"]), 0.5))
        painter.drawLine(
            QPointF(8, self._header_h),
            QPointF(self._width - 8, self._header_h),
        )

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for port in self._input_ports + self._output_ports:
                for edge in port.connected_edges:
                    edge.update_path()
        return super().itemChange(change, value)
