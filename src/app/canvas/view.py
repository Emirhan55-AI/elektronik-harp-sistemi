"""
NodeEditorView - QGraphicsView based editor view.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, Signal
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QWheelEvent,
)
from PySide6.QtWidgets import QGraphicsView, QRubberBand

_MIME_NODE_TYPE = "application/x-eh-node-type"


class NodeEditorView(QGraphicsView):
    """Pan/zoom capable node editor view with selection and shortcuts."""

    node_drop_requested = Signal(str, QPointF)
    copy_requested = Signal()
    paste_requested = Signal()
    undo_requested = Signal()
    delete_requested = Signal()

    def __init__(self, scene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)

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
        self.setAcceptDrops(True)

        self._zoom = 1.0
        self._zoom_min = 0.15
        self._zoom_max = 5.0
        self._pan_active = False
        self._pan_start = QPointF()
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self._rubber_origin = QPoint()
        self._selection_active = False
        self._rubber_current = QPoint()
        self._selection_threshold = 6
        self._selection_operation = Qt.ItemSelectionOperation.ReplaceSelection

    def wheelEvent(self, event: QWheelEvent) -> None:
        factor = 1.15
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor

        new_zoom = self._zoom * factor
        if self._zoom_min <= new_zoom <= self._zoom_max:
            self._zoom = new_zoom
            self.scale(factor, factor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_active = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton and not self._scene_item_at(event.pos()):
            self._selection_active = True
            self._rubber_origin = event.pos()
            self._rubber_current = event.pos()
            self._rubber_band.setGeometry(QRect(self._rubber_origin, self._rubber_origin))
            self._selection_operation = (
                Qt.ItemSelectionOperation.AddToSelection
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier
                else Qt.ItemSelectionOperation.ReplaceSelection
            )
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.scene().clearSelection()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_active:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            return

        if self._selection_active:
            self._rubber_current = event.pos()
            if (event.pos() - self._rubber_origin).manhattanLength() < self._selection_threshold:
                return
            rect = QRect(self._rubber_origin, event.pos()).normalized()
            self._rubber_band.setGeometry(rect)
            self._update_rubber_band_style(event.pos())
            if not self._rubber_band.isVisible():
                self._rubber_band.show()
            self._apply_rubber_selection(rect, event.pos())
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_active = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton and self._selection_active:
            rect = self._rubber_band.geometry()
            if self._rubber_band.isVisible():
                self._apply_rubber_selection(rect, self._rubber_current)
            self._rubber_band.hide()
            self._selection_active = False
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self.itemAt(event.pos()) is None:
            self.reset_view()
            return
        super().mouseDoubleClickEvent(event)

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
            self.node_drop_requested.emit(node_type_id, self.mapToScene(event.position().toPoint()))
            event.acceptProposedAction()
        else:
            event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Home, Qt.Key.Key_F):
            self.fit_all()
            return
        if event.matches(QKeySequence.StandardKey.SelectAll):
            for item in self.scene().items():
                item.setSelected(True)
            return
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_requested.emit()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_requested.emit()
            return
        if event.matches(QKeySequence.StandardKey.Undo):
            self.undo_requested.emit()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
            return
        super().keyPressEvent(event)

    def reset_view(self) -> None:
        self.resetTransform()
        self._zoom = 1.0
        self.centerOn(0, 0)

    def fit_all(self) -> None:
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

    def _scene_item_at(self, pos: QPoint):
        return self.itemAt(pos)

    def _apply_rubber_selection(self, rect: QRect, current_pos: QPoint) -> None:
        if rect.isNull():
            return
        scene_rect = self.mapToScene(rect).boundingRect()
        path = QPainterPath()
        path.addRect(scene_rect)
        mode = (
            Qt.ItemSelectionMode.ContainsItemShape
            if current_pos.x() >= self._rubber_origin.x()
            else Qt.ItemSelectionMode.IntersectsItemShape
        )
        self.scene().setSelectionArea(
            path,
            self._selection_operation,
            mode,
            self.viewportTransform(),
        )

    def _update_rubber_band_style(self, current_pos: QPoint) -> None:
        is_left_to_right = current_pos.x() >= self._rubber_origin.x()
        if is_left_to_right:
            border = "rgba(96, 176, 255, 0.98)"
            fill = "rgba(96, 176, 255, 0.30)"
        else:
            border = "rgba(0, 255, 170, 1.0)"
            fill = "rgba(0, 255, 170, 0.34)"
        self._rubber_band.setStyleSheet(
            f"QRubberBand {{ border: 2px solid {border}; background-color: {fill}; }}"
        )


