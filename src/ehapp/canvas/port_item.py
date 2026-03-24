"""
PortItem — QGraphicsEllipseItem tabanlı port görseli.

Her node'un giriş ve çıkış portları bu item ile temsil edilir.
Bağlantı başlatma/sonlandırma buradaki mousePress ile tetiklenir.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen, QPainter
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsSceneMouseEvent,
)

from ehapp.theme.tokens import COLORS, PORT_COLORS, SIZES
from ehcore.contracts import PortDef


class PortItem(QGraphicsEllipseItem):
    """Tek bir input veya output portu."""

    def __init__(
        self,
        port_def: PortDef,
        is_output: bool,
        parent: QGraphicsItem | None = None,
    ) -> None:
        r = SIZES["node_port_radius"]
        super().__init__(-r, -r, 2 * r, 2 * r, parent)

        self.port_def = port_def
        self.is_output = is_output
        self._edges: list = []  # Bağlı edge'ler

        # Renk
        color_key = port_def.port_type.name
        color_hex = PORT_COLORS.get(color_key, COLORS["port_any"])
        self._color = QColor(color_hex)
        self._hover_color = self._color.lighter(140)

        self.setBrush(QBrush(self._color))
        self.setPen(QPen(self._color.darker(120), 1.5))

        self.setAcceptHoverEvents(True)
        self.setToolTip(f"{port_def.display_name} ({port_def.port_type.name})")
        self.setZValue(2)
        # Portlar node ile birlikte hareket ettiği için kendi itemChange'lerine gerek yok

    @property
    def center_scene_pos(self) -> QPointF:
        """Port'un sahne koordinatındaki merkez noktası (scale bağımsız)."""
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

    # ── Hover ────────────────────────────────────────────────────

    def hoverEnterEvent(self, event) -> None:
        self.setBrush(QBrush(self._hover_color))
        self.setPen(QPen(self._color.lighter(160), 2.5))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setBrush(QBrush(self._color))
        self.setPen(QPen(self._color.darker(120), 1.5))
        super().hoverLeaveEvent(event)
