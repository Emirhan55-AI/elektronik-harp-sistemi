"""
NodeItem — QGraphicsItem tabanlı node kutusu.

Her node, başlık + portlar + gövde yapısındadır.
Taşınabilir, seçilebilir, çift tıklanabilir.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QPointF
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient,
    QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsTextItem,
    QGraphicsDropShadowEffect,
)

from ehapp.theme.tokens import COLORS, FONTS, SIZES
from ehcore.contracts import NodeDescriptor
from .port_item import PortItem


class NodeItem(QGraphicsItem):
    """Pipeline canvas'ındaki tek bir node kutusu."""

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

        # Boyutlar
        self._min_width = SIZES["node_min_width"]
        self._header_h = SIZES["node_header_h"]
        self._port_spacing = SIZES["node_port_spacing"]
        self._border_w = SIZES["node_border"]
        self._radius = SIZES["radius_lg"]

        # Portlar
        self._input_ports: list[PortItem] = []
        self._output_ports: list[PortItem] = []

        # Boyut hesapla
        n_ports = max(len(descriptor.input_ports), len(descriptor.output_ports), 1)
        self._body_h = n_ports * self._port_spacing + 12
        self._width = self._min_width
        self._height = self._header_h + self._body_h

        # Renkler
        self._bg_color = QColor(COLORS["node_bg"])
        self._header_color = QColor(COLORS["node_header"])
        self._border_color = QColor(COLORS["border_default"])
        self._selected_border = QColor(COLORS["node_selected"])
        self._text_color = QColor(COLORS["text_primary"])

        # State göstergesi
        self._state = "idle"  # "idle", "running", "error"

        # Qt ayarları
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

        # Parlama efekti
        self._glow_effect = QGraphicsDropShadowEffect()
        self._glow_effect.setBlurRadius(25)
        self._glow_effect.setColor(QColor(COLORS["success"])) # Modern yeşil/mavi parıltı
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setEnabled(False)
        self.setGraphicsEffect(self._glow_effect)

        # Başlık metni
        self._title_item = QGraphicsTextItem(descriptor.display_name, self)
        self._title_item.setDefaultTextColor(self._text_color)
        font = QFont(FONTS["family"], FONTS["size_sm"])
        font.setWeight(QFont.Weight.Medium)
        self._title_item.setFont(font)
        self._title_item.setPos(8, 3)

        # Genişliği başlık metnine göre ayarla
        text_width = self._title_item.boundingRect().width() + 20
        self._width = max(self._min_width, text_width)

        # Portları oluştur
        self._create_ports()

    def _create_ports(self) -> None:
        """Input ve output portlarını oluştur ve yerleştir."""
        # Input portlar (sol taraf)
        for i, port_def in enumerate(self.descriptor.input_ports):
            port = PortItem(port_def, is_output=False, parent=self)
            y = self._header_h + 12 + i * self._port_spacing
            port.setPos(0, y)
            self._input_ports.append(port)

        # Output portlar (sağ taraf)
        for i, port_def in enumerate(self.descriptor.output_ports):
            port = PortItem(port_def, is_output=True, parent=self)
            y = self._header_h + 12 + i * self._port_spacing
            port.setPos(self._width, y)
            self._output_ports.append(port)

    @property
    def input_ports(self) -> list[PortItem]:
        return self._input_ports

    @property
    def output_ports(self) -> list[PortItem]:
        return self._output_ports

    def get_port(self, name: str) -> PortItem | None:
        """Port'u isme göre bul."""
        for p in self._input_ports + self._output_ports:
            if p.port_def.name == name:
                return p
        return None

    def set_state(self, state: str) -> None:
        """Node state'ini güncelle (idle/running/error)."""
        self._state = state
        if state == "running":
            self._glow_effect.setEnabled(True)
        else:
            self._glow_effect.setEnabled(False)
        self.update()

    # ── QGraphicsItem overrides ──────────────────────────────────

    def boundingRect(self) -> QRectF:
        m = self._border_w
        return QRectF(-m, -m, self._width + 2 * m, self._height + 2 * m)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self._width, self._height)
        header_rect = QRectF(0, 0, self._width, self._header_h)

        # ── Gölge ──
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(rect.adjusted(2, 2, 2, 2), self._radius, self._radius)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 60))

        # ── Gövde ──
        body_path = QPainterPath()
        body_path.addRoundedRect(rect, self._radius, self._radius)
        painter.fillPath(body_path, QBrush(self._bg_color))

        # ── Başlık gradient ──
        gradient = QLinearGradient(0, 0, 0, self._header_h)
        gradient.setColorAt(0, self._header_color)
        gradient.setColorAt(1, self._bg_color)

        header_path = QPainterPath()
        header_path.addRoundedRect(header_rect, self._radius, self._radius)
        # Alt köşeleri düzelt
        header_path.addRect(QRectF(0, self._header_h - self._radius, self._width, self._radius))
        painter.fillPath(header_path, QBrush(gradient))

        # ── Kenarlık ──
        border_color = self._border_color
        border_width = self._border_w

        if self.isSelected():
            border_color = self._selected_border
            border_width = 2.5
        elif self._state == "running":
            border_color = QColor(COLORS["node_running"])
        elif self._state == "error":
            border_color = QColor(COLORS["node_error"])

        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(rect, self._radius, self._radius)

        # ── State göstergesi (küçük daire) ──
        if self._state != "idle":
            indicator_color = (
                QColor(COLORS["node_running"])
                if self._state == "running"
                else QColor(COLORS["node_error"])
            )
            painter.setBrush(QBrush(indicator_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QPointF(self._width - 12, 10), 4, 4
            )

        # ── Başlık ayırıcı çizgi ──
        painter.setPen(QPen(QColor(COLORS["border_default"]), 0.5))
        painter.drawLine(
            QPointF(8, self._header_h),
            QPointF(self._width - 8, self._header_h),
        )

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Port'ların edge'lerini güncelle
            for port in self._input_ports + self._output_ports:
                for edge in port.connected_edges:
                    edge.update_path()
        return super().itemChange(change, value)
