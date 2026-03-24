"""
NodeEditorScene - QGraphicsScene based node editor scene.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QTransform
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent, QGraphicsView, QMenu

from ehapp.strings import tr
from ehapp.theme.tokens import COLORS
from ehcore.contracts import NodeDescriptor, check_port_compatibility
from ehcore.registry import NodeRegistry

from .edge_item import EdgeItem
from .node_item import NodeItem
from .port_item import PortItem


class NodeEditorScene(QGraphicsScene):
    """Node editor scene with connection and interaction management."""

    node_added = Signal(str, str)
    node_removed = Signal(str)
    edge_added = Signal(str, str, str, str)
    edge_removed = Signal(str, str, str, str)
    node_selected = Signal(str)
    node_double_clicked = Signal(str)
    context_add_requested = Signal(str, QPointF)
    delete_requested = Signal()
    node_delete_requested = Signal(str)
    node_disconnect_requested = Signal(str)
    nodes_move_started = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setBackgroundBrush(QColor(COLORS["bg_primary"]))

        self._nodes: dict[str, NodeItem] = {}
        self._edges: list[EdgeItem] = []

        self._drawing_edge: EdgeItem | None = None
        self._drawing_source_port: PortItem | None = None
        self._move_candidate = False
        self._move_started = False
        self._move_press_pos = QPointF()

        self._grid_size = 20
        self._grid_bold_every = 5
        self._grid_visible = True

    def drawBackground(self, painter: QPainter, rect) -> None:
        super().drawBackground(painter, rect)
        if not self._grid_visible:
            return

        grid = self._grid_size
        bold_n = self._grid_bold_every

        left = int(rect.left()) - (int(rect.left()) % grid)
        top = int(rect.top()) - (int(rect.top()) % grid)

        painter.setPen(QPen(QColor(COLORS["grid_line"]), 0.5))
        x = left
        while x <= rect.right():
            if x % (grid * bold_n) != 0:
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            x += grid

        y = top
        while y <= rect.bottom():
            if y % (grid * bold_n) != 0:
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
            y += grid

        painter.setPen(QPen(QColor(COLORS["grid_line_bold"]), 1.0))
        bold_grid = grid * bold_n
        left_b = int(rect.left()) - (int(rect.left()) % bold_grid)
        top_b = int(rect.top()) - (int(rect.top()) % bold_grid)

        x = left_b
        while x <= rect.right():
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            x += bold_grid

        y = top_b
        while y <= rect.bottom():
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
            y += bold_grid

    def add_node(
        self,
        instance_id: str,
        descriptor: NodeDescriptor,
        position: QPointF | None = None,
        config: dict | None = None,
    ) -> NodeItem:
        node = NodeItem(instance_id, descriptor, config)
        if position is not None:
            node.setPos(position)
        self.addItem(node)
        self._nodes[instance_id] = node
        self.node_added.emit(instance_id, descriptor.node_id)
        return node

    def remove_node(self, instance_id: str) -> None:
        node = self._nodes.get(instance_id)
        if node is None:
            return

        for port in node.input_ports + node.output_ports:
            for edge in list(port.connected_edges):
                self.remove_edge(edge)

        self.removeItem(node)
        self._nodes.pop(instance_id, None)
        self.node_removed.emit(instance_id)

    def get_node(self, instance_id: str) -> NodeItem | None:
        return self._nodes.get(instance_id)

    @property
    def node_items(self) -> dict[str, NodeItem]:
        return dict(self._nodes)

    @property
    def edge_items(self) -> list[EdgeItem]:
        return list(self._edges)

    def add_edge_between(
        self,
        source_node_id: str,
        source_port_name: str,
        target_node_id: str,
        target_port_name: str,
        emit_signal: bool = True,
    ) -> EdgeItem | None:
        src_node = self._nodes.get(source_node_id)
        tgt_node = self._nodes.get(target_node_id)
        if src_node is None or tgt_node is None:
            return None

        src_port = src_node.get_port(source_port_name)
        tgt_port = tgt_node.get_port(target_port_name)
        if src_port is None or tgt_port is None:
            return None

        edge = EdgeItem(src_port, tgt_port)
        self.addItem(edge)
        self._edges.append(edge)
        if emit_signal:
            self.edge_added.emit(
                source_node_id,
                source_port_name,
                target_node_id,
                target_port_name,
            )
        return edge

    def remove_edge(self, edge: EdgeItem, emit_signal: bool = True) -> None:
        source_node = self._find_node_for_port(edge.source_port) if edge.source_port else None
        target_node = self._find_node_for_port(edge.target_port) if edge.target_port else None

        edge.disconnect_ports()
        if edge in self._edges:
            self._edges.remove(edge)
        self.removeItem(edge)
        if emit_signal and source_node is not None and target_node is not None:
            self.edge_removed.emit(
                source_node.instance_id,
                edge.source_port.port_def.name,
                target_node.instance_id,
                edge.target_port.port_def.name,
            )

    def remove_edge_between(
        self,
        source_node_id: str,
        source_port_name: str,
        target_node_id: str,
        target_port_name: str,
        emit_signal: bool = True,
    ) -> bool:
        for edge in list(self._edges):
            source_node = self._find_node_for_port(edge.source_port) if edge.source_port else None
            target_node = self._find_node_for_port(edge.target_port) if edge.target_port else None
            if source_node is None or target_node is None:
                continue
            if (
                source_node.instance_id == source_node_id
                and edge.source_port.port_def.name == source_port_name
                and target_node.instance_id == target_node_id
                and edge.target_port.port_def.name == target_port_name
            ):
                self.remove_edge(edge, emit_signal=emit_signal)
                return True
        return False

    def start_edge_drawing(self, port: PortItem) -> None:
        self._drawing_source_port = port
        self._drawing_edge = EdgeItem(source_port=port, target_port=None)
        self.addItem(self._drawing_edge)
        self._apply_edge_preview_states(port)

    def update_edge_drawing(self, scene_pos: QPointF) -> None:
        if self._drawing_edge is not None:
            self._drawing_edge.set_preview_end(scene_pos)

    def finish_edge_drawing(self, target_port: PortItem | None) -> bool:
        if self._drawing_edge is None or self._drawing_source_port is None:
            return False

        success = False
        if target_port is not None and target_port is not self._drawing_source_port:
            src = self._drawing_source_port
            tgt = target_port

            if src.is_output and not tgt.is_output:
                if not tgt.is_connected and check_port_compatibility(src.port_def.port_type, tgt.port_def.port_type):
                    self._drawing_edge.complete_connection(tgt)
                    self._edges.append(self._drawing_edge)
                    src_node = self._find_node_for_port(src)
                    tgt_node = self._find_node_for_port(tgt)
                    if src_node and tgt_node:
                        self.edge_added.emit(
                            src_node.instance_id,
                            src.port_def.name,
                            tgt_node.instance_id,
                            tgt.port_def.name,
                        )
                    success = True
            elif not src.is_output and tgt.is_output:
                if not src.is_connected and check_port_compatibility(tgt.port_def.port_type, src.port_def.port_type):
                    self.removeItem(self._drawing_edge)
                    edge = EdgeItem(tgt, src)
                    self.addItem(edge)
                    self._edges.append(edge)

                    src_node = self._find_node_for_port(tgt)
                    tgt_node = self._find_node_for_port(src)
                    if src_node and tgt_node:
                        self.edge_added.emit(
                            src_node.instance_id,
                            tgt.port_def.name,
                            tgt_node.instance_id,
                            src.port_def.name,
                        )
                    success = True

        if not success:
            self.removeItem(self._drawing_edge)

        self._drawing_edge = None
        self._drawing_source_port = None
        self._clear_port_preview_states()
        return success

    def cancel_edge_drawing(self) -> None:
        if self._drawing_edge:
            self.removeItem(self._drawing_edge)
            self._drawing_edge = None
            self._drawing_source_port = None
        self._clear_port_preview_states()

    @property
    def is_drawing_edge(self) -> bool:
        return self._drawing_edge is not None

    def get_selected_nodes(self) -> list[NodeItem]:
        return [item for item in self.selectedItems() if isinstance(item, NodeItem)]

    def get_selected_edges(self) -> list[EdgeItem]:
        return [item for item in self.selectedItems() if isinstance(item, EdgeItem)]

    def delete_selected(self) -> None:
        for edge in self.get_selected_edges():
            self.remove_edge(edge)
        for node in self.get_selected_nodes():
            self.remove_node(node.instance_id)

    def clear_all(self) -> None:
        for edge in list(self._edges):
            self.remove_edge(edge)
        for nid in list(self._nodes.keys()):
            self.remove_node(nid)
        self._clear_port_preview_states()

    def _find_node_for_port(self, port: PortItem) -> NodeItem | None:
        for node in self._nodes.values():
            if port in node.input_ports or port in node.output_ports:
                return node
        return None

    def _resolve_node_from_item(self, item) -> NodeItem | None:
        current = item
        while current is not None:
            if isinstance(current, NodeItem):
                return current
            current = current.parentItem()
        return None

    def _clear_port_preview_states(self) -> None:
        for node in self._nodes.values():
            for port in node.input_ports + node.output_ports:
                port.set_preview_state(None)

    def _apply_edge_preview_states(self, source_port: PortItem) -> None:
        self._clear_port_preview_states()
        source_port.set_preview_state("source")
        for node in self._nodes.values():
            for port in node.input_ports + node.output_ports:
                if port is source_port or port.is_output == source_port.is_output:
                    continue
                if source_port.is_output:
                    is_ok = (
                        (not port.is_connected)
                        and check_port_compatibility(source_port.port_def.port_type, port.port_def.port_type)
                    )
                else:
                    is_ok = (
                        (not source_port.is_connected)
                        and check_port_compatibility(port.port_def.port_type, source_port.port_def.port_type)
                    )
                port.set_preview_state("compatible" if is_ok else "incompatible")

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())
        self._move_candidate = False
        self._move_started = False
        self._move_press_pos = event.scenePos()

        if isinstance(item, PortItem) and event.button() == Qt.MouseButton.LeftButton:
            self.start_edge_drawing(item)
            return

        if event.button() == Qt.MouseButton.LeftButton and self._resolve_node_from_item(item) is not None:
            self._move_candidate = True

        super().mousePressEvent(event)

        node = self._resolve_node_from_item(item)
        if node is not None:
            self.node_selected.emit(node.instance_id)
            return

        selected = self.get_selected_nodes()
        if len(selected) == 1:
            self.node_selected.emit(selected[0].instance_id)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.is_drawing_edge:
            self.update_edge_drawing(event.scenePos())
            return
        if self._move_candidate and not self._move_started:
            if (event.scenePos() - self._move_press_pos).manhattanLength() > 6:
                self._move_started = True
                self.nodes_move_started.emit()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.is_drawing_edge and event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())
            target = item if isinstance(item, PortItem) else None
            self.finish_edge_drawing(target)
            self._move_candidate = False
            self._move_started = False
            return
        super().mouseReleaseEvent(event)
        self._move_candidate = False
        self._move_started = False

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())
        node = self._resolve_node_from_item(item)
        if node is not None:
            self.node_double_clicked.emit(node.instance_id)
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_edge_drawing()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        pos = event.scenePos()
        transform = self.views()[0].transform() if self.views() else QTransform()
        item = self.itemAt(pos, transform)

        menu = QMenu()
        menu.setStyleSheet(
            f"QMenu {{ background: {COLORS['bg_secondary']}; "
            f"color: {COLORS['text_primary']}; border: 1px solid {COLORS['border_default']}; }}"
            f"QMenu::item:selected {{ background: {COLORS['bg_elevated']}; }}"
        )

        node = self._resolve_node_from_item(item)
        if node is not None:
            self._handle_node_context_menu(menu, node, event)
        else:
            self._handle_scene_context_menu(menu, pos, event)

    def _handle_node_context_menu(self, menu: QMenu, node: NodeItem, event) -> None:
        act_props = menu.addAction(tr.CTX_PROPERTIES)
        act_disconnect = menu.addAction(tr.CTX_DISCONNECT)
        menu.addSeparator()
        act_delete = menu.addAction(tr.CTX_DELETE)

        chosen = menu.exec(event.screenPos())
        if chosen == act_props:
            self.node_double_clicked.emit(node.instance_id)
        elif chosen == act_disconnect:
            self.node_disconnect_requested.emit(node.instance_id)
        elif chosen == act_delete:
            self.node_delete_requested.emit(node.instance_id)

    def _handle_scene_context_menu(self, menu: QMenu, pos: QPointF, event) -> None:
        add_menu = menu.addMenu(tr.CTX_ADD_BLOCK)
        categories = NodeRegistry.get_categories()
        type_actions = {}
        for cat_name, descriptors in sorted(categories.items()):
            cat_sub = add_menu.addMenu(cat_name)
            for desc in descriptors:
                act = cat_sub.addAction(desc.display_name)
                type_actions[act] = (desc.node_id, pos)

        menu.addSeparator()
        act_select_all = menu.addAction(tr.CTX_SELECT_ALL)
        act_fit = menu.addAction(tr.CTX_FIT_ALL)
        act_reset = menu.addAction(tr.CTX_RESET_VIEW)

        chosen = menu.exec(event.screenPos())
        if chosen in type_actions:
            node_type_id, drop_pos = type_actions[chosen]
            self.context_add_requested.emit(node_type_id, drop_pos)
        elif chosen == act_select_all:
            for item in self.items():
                item.setSelected(True)
        elif chosen == act_fit:
            for view in self.views():
                if isinstance(view, QGraphicsView):
                    rect = self.itemsBoundingRect()
                    if not rect.isEmpty():
                        view.fitInView(rect.adjusted(-50, -50, 50, 50), Qt.AspectRatioMode.KeepAspectRatio)
        elif chosen == act_reset:
            for view in self.views():
                if isinstance(view, QGraphicsView):
                    view.resetTransform()
                    view.centerOn(0, 0)
