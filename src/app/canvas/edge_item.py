"""
EdgeItem — Bezier eğrili bağlantı çizgisi.

İki port arasında veya çizim sırasında mouse'a doğru çizilir.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsDropShadowEffect,
)

from app.theme.tokens import COLORS


class EdgeItem(QGraphicsPathItem):
    """İki port arasındaki bağlantı çizgisi (bezier)."""

    def __init__(
        self,
        source_port=None,
        target_port=None,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)

        self.source_port = source_port
        self.target_port = target_port

        # Stil
        self._color = QColor(COLORS["edge_default"])
        self._color_active = QColor(COLORS["edge_active"])
        self._color_preview = QColor(COLORS["edge_preview"])
        self._width = 2.5

        self._is_preview = (target_port is None)
        self._preview_end: QPointF = QPointF(0, 0)

        pen_color = self._color_preview if self._is_preview else self._color
        self.setPen(QPen(pen_color, self._width, Qt.PenStyle.SolidLine))
        self.setZValue(0)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        # Animasyon state ve Timer
        from PySide6.QtCore import QTimer
        self._state = "idle"
        self._dash_offset = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._advance_dash)

        # Glow Efekti (Veri Akarken)
        self._glow_effect = QGraphicsDropShadowEffect()
        self._glow_effect.setBlurRadius(15)
        self._glow_effect.setColor(QColor(COLORS["success"]))
        self._glow_effect.setOffset(0, 0)
        self._glow_effect.setEnabled(False)
        self.setGraphicsEffect(self._glow_effect)

        self._runtime_debug_text = ""

        if source_port and target_port:
            source_port.add_edge(self)
            target_port.add_edge(self)
            self.update_path()

    def set_preview_end(self, pos: QPointF) -> None:
        """Preview modunda mouse pozisyonunu ayarla."""
        self._preview_end = pos
        self.update_path()

    def complete_connection(self, target_port) -> None:
        """Preview'dan gerçek bağlantıya geçiş."""
        self.target_port = target_port
        self._is_preview = False
        if self.source_port is not None:
            self.source_port.add_edge(self)
        target_port.add_edge(self)
        self.setPen(QPen(self._color, self._width, Qt.PenStyle.SolidLine))
        self.update_path()

    def update_path(self) -> None:
        """Bezier yolunu güncelle."""
        if self.source_port is None:
            return

        self.prepareGeometryChange()
        start = self.source_port.center_scene_pos
        end = (
            self.target_port.center_scene_pos
            if self.target_port is not None
            else self._preview_end
        )

        path = QPainterPath(start)

        # Bezier kontrol noktaları — yatay mesafeye orantılı
        dx = abs(end.x() - start.x()) * 0.5
        dx = max(dx, 50)  # Minimum eğrilik

        ctrl1 = QPointF(start.x() + dx, start.y())
        ctrl2 = QPointF(end.x() - dx, end.y())

        path.cubicTo(ctrl1, ctrl2, end)
        self.setPath(path)

    def disconnect_ports(self) -> None:
        """Port referanslarını temizle."""
        if self.source_port:
            self.source_port.remove_edge(self)
        if self.target_port:
            self.target_port.remove_edge(self)

    # ── Seçim ve Animasyon stili ─────────────────────────────────

    def set_state(self, state: str) -> None:
        self._state = state
        if state == "running":
            self._timer.start(50)  # 20 FPS (Saniyede 20 kere akış frame'i)
            self._glow_effect.setEnabled(True)
            self._glow_effect.setColor(QColor(COLORS["success"]))
        elif state == "warning":
            self._timer.stop()
            self._glow_effect.setEnabled(True)
            self._glow_effect.setColor(QColor(COLORS["warning"]))
        elif state == "stale":
            self._timer.stop()
            self._glow_effect.setEnabled(True)
            self._glow_effect.setColor(QColor(COLORS["info"]))
        else:
            self._timer.stop()
            self._glow_effect.setEnabled(False)
        self.update()

    def set_runtime_debug_info(self, text: str, state: str = "idle") -> None:
        self._runtime_debug_text = text
        self.setToolTip(text)
        self.set_state(state)

    def _advance_dash(self) -> None:
        self._dash_offset -= 2  # Akış hızı
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        pen = QPen(self._color, self._width, Qt.PenStyle.SolidLine)
        
        if self.isSelected():
            pen = QPen(self._color_active, self._width + 1.5, Qt.PenStyle.SolidLine)
        elif self._state == "running":
            # Neon Veri Akışı
            pen = QPen(QColor(COLORS["success"]), self._width + 0.5, Qt.PenStyle.DashLine)
            pen.setDashPattern([6, 4])
            pen.setDashOffset(self._dash_offset)
        elif self._state == "warning":
            pen = QPen(QColor(COLORS["warning"]), self._width + 0.5, Qt.PenStyle.SolidLine)
        elif self._state == "stale":
            pen = QPen(QColor(COLORS["info"]), self._width, Qt.PenStyle.DashLine)
            pen.setDashPattern([3, 5])
        elif self._is_preview:
            pen = QPen(self._color_preview, self._width, Qt.PenStyle.SolidLine)

        self.setPen(pen)
        super().paint(painter, option, widget)


