"""
NodeEditorView — QGraphicsView tabanlı görünüm.

Pan (orta tık sürükle), zoom (mouse wheel), shortcut'lar.
Sürükle-bırak ile palette'ten blok ekleme destekli.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QPainter, QWheelEvent, QMouseEvent, QKeyEvent, QDragEnterEvent, QDropEvent, QDragMoveEvent
from PySide6.QtWidgets import QGraphicsView

from ehapp.theme.tokens import COLORS

_MIME_NODE_TYPE = "application/x-eh-node-type"


class NodeEditorView(QGraphicsView):
    """Pan/zoom destekli node editör görünümü — drag-drop destekli."""

    # Palette'ten sürükle-bırak sinyali
    node_drop_requested = Signal(str, QPointF)  # (node_type_id, scene_pos)

    def __init__(self, scene, parent=None) -> None:
        super().__init__(scene, parent)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        # Drag-drop kabul
        self.setAcceptDrops(True)

        self._zoom = 1.0
        self._zoom_min = 0.15
        self._zoom_max = 5.0
        self._pan_active = False
        self._pan_start: QPointF = QPointF()

    # ── Zoom ─────────────────────────────────────────────────────

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor

        new_zoom = self._zoom * factor
        if self._zoom_min <= new_zoom <= self._zoom_max:
            self._zoom = new_zoom
            self.scale(factor, factor)

    # ── Pan (orta tık sürükle) ───────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_active = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_active:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_active = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # Boş alana çift tık → görünümü sıfırla
        item = self.itemAt(event.pos())
        if item is None:
            self.reset_view()
            return
        super().mouseDoubleClickEvent(event)

    # ── Drag & Drop (Palette'ten) ────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(_MIME_NODE_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(_MIME_NODE_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasFormat(_MIME_NODE_TYPE):
            node_type_id = event.mimeData().data(_MIME_NODE_TYPE).data().decode("utf-8")
            scene_pos = self.mapToScene(event.position().toPoint())
            self.node_drop_requested.emit(node_type_id, scene_pos)
            event.acceptProposedAction()
        else:
            event.ignore()

    # ── Kısayollar ───────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # Home veya F → görünümü sıfırla
        if event.key() in (Qt.Key.Key_Home, Qt.Key.Key_F):
            self.fit_all()
            return
        # Ctrl+A → tümünü seç
        if event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            for item in self.scene().items():
                item.setSelected(True)
            return
        super().keyPressEvent(event)

    # ── Görünüm kontrolleri ──────────────────────────────────────

    def reset_view(self) -> None:
        """Zoom ve pan'ı sıfırla."""
        self.resetTransform()
        self._zoom = 1.0
        self.centerOn(0, 0)

    def fit_all(self) -> None:
        """Tüm node'ları görünür alana sığdır."""
        rect = self.scene().itemsBoundingRect()
        if not rect.isEmpty():
            self.fitInView(rect.adjusted(-50, -50, 50, 50), Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom = self.transform().m11()

    def zoom_in(self) -> None:
        factor = 1.25
        if self._zoom * factor <= self._zoom_max:
            self._zoom *= factor
            self.scale(factor, factor)

    def zoom_out(self) -> None:
        factor = 1.0 / 1.25
        if self._zoom * factor >= self._zoom_min:
            self._zoom *= factor
            self.scale(factor, factor)
