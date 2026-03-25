"""
PortItem - Visual port item used by node blocks.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem

from app.theme.tokens import COLORS, PORT_COLORS, SIZES
from ehplatform.contracts import PortDef


class PortItem(QGraphicsEllipseItem):
    """Single input or output port."""

    def __init__(
        self,
        port_def: PortDef,
        is_output: bool,
        parent: QGraphicsItem | None = None,
    ) -> None:
        radius = (
            SIZES["node_port_radius"]
            if port_def.required
            else max(4, SIZES["node_port_radius"] - 2)
        )
        super().__init__(-radius, -radius, 2 * radius, 2 * radius, parent)

        self.port_def = port_def
        self.is_output = is_output
        self._edges: list = []
        self._is_optional = not port_def.required
        self._validation_state = "normal"
        self._preview_state: str | None = None

        color_key = port_def.port_type.name
        color_hex = PORT_COLORS.get(color_key, COLORS["port_any"])
        self._base_color = QColor(color_hex)
        self._hover_color = self._base_color.lighter(140)

        self.setAcceptHoverEvents(True)
        self.setToolTip(port_def.tooltip)
        self.setZValue(2)
        self._apply_style()

    @property
    def center_scene_pos(self) -> QPointF:
        """Port center in scene coordinates."""
        return self.mapToScene(self.boundingRect().center())

    def add_edge(self, edge) -> None:
        if edge not in self._edges:
            self._edges.append(edge)

    def remove_edge(self, edge) -> None:
        if edge in self._edges:
            self._edges.remove(edge)

    @property
    def connected_edges(self) -> list:
        return list(self._edges)

    @property
    def is_connected(self) -> bool:
        return len(self._edges) > 0

    def set_validation_state(self, state: str) -> None:
        self._validation_state = state
        self._apply_style()

    def set_preview_state(self, state: str | None) -> None:
        self._preview_state = state
        self._apply_style()

    def hoverEnterEvent(self, event) -> None:
        self._apply_style(hovered=True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._apply_style()
        super().hoverLeaveEvent(event)

    def _current_state(self) -> str:
        return self._preview_state or self._validation_state

    def _apply_style(self, hovered: bool = False) -> None:
        state = self._current_state()
        color = QColor(self._base_color)
        pen_color = QColor(self._base_color.darker(120))
        pen_width = 1.0 if self._is_optional else 1.5

        if state == "warning":
            color = QColor(COLORS["warning"])
            pen_color = QColor(COLORS["warning"])
        elif state == "compatible":
            color = QColor(COLORS["success"])
            pen_color = QColor(COLORS["success"])
        elif state == "incompatible":
            color = QColor(COLORS["error"])
            pen_color = QColor(COLORS["error"])
        elif state == "source":
            color = QColor(COLORS["accent_primary"])
            pen_color = QColor(COLORS["accent_primary"])

        if self._is_optional and state in {"normal", "warning"}:
            color.setAlpha(150 if state == "normal" else 180)
            pen_color.setAlpha(170 if state == "normal" else 200)

        if hovered:
            color = color.lighter(140)
            pen_color = pen_color.lighter(160)
            pen_width = 1.8 if self._is_optional else 2.5

        self.setBrush(QBrush(color))
        self.setPen(QPen(pen_color, pen_width))


