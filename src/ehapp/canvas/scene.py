"""
NodeEditorScene — QGraphicsScene tabanlı node editör sahnesi.

Node ekleme, silme, bağlantı kurma, çizim preview'ı yönetir.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QTransform
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QMenu,
    QGraphicsView,
)

from ehapp.theme.tokens import COLORS
from ehapp.strings import tr
from ehcore.contracts import NodeDescriptor, check_port_compatibility
from ehcore.registry import NodeRegistry

from .node_item import NodeItem
from .port_item import PortItem
from .edge_item import EdgeItem


class NodeEditorScene(QGraphicsScene):
    """Node editör sahnesi — bağlantı ve etkileşim yönetimi."""

    # Sinyaller
    node_added = Signal(str, str)          # (instance_id, node_type_id)
    node_removed = Signal(str)             # (instance_id)
    edge_added = Signal(str, str, str, str)  # (src_node, src_port, tgt_node, tgt_port)
    edge_removed = Signal()
    node_selected = Signal(str)            # (instance_id) — properties panel için
    node_double_clicked = Signal(str)      # (instance_id) — properties aç
    context_add_requested = Signal(str, QPointF)  # (node_type_id, pos) — sağ tık menüden ekleme

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.setBackgroundBrush(QColor(COLORS["bg_primary"]))

        self._nodes: dict[str, NodeItem] = {}
        self._edges: list[EdgeItem] = []

        # Bağlantı çizim durumu
        self._drawing_edge: EdgeItem | None = None
        self._drawing_source_port: PortItem | None = None

        # Grid ayarları
        self._grid_size = 20       # İnce grid aralık (px)
        self._grid_bold_every = 5  # Her 5 çizgide bir kalın
        self._grid_visible = True

    # ── Grid Çizimi ──────────────────────────────────────────────

    def drawBackground(self, painter: QPainter, rect) -> None:
        """Altium benzeri grid arka plan çiz."""
        super().drawBackground(painter, rect)

        if not self._grid_visible:
            return

        grid = self._grid_size
        bold_n = self._grid_bold_every

        left = int(rect.left()) - (int(rect.left()) % grid)
        top = int(rect.top()) - (int(rect.top()) % grid)

        # İnce çizgiler
        pen_fine = QPen(QColor(COLORS["grid_line"]), 0.5)
        painter.setPen(pen_fine)

        x = left
        while x <= rect.right():
            if x % (grid * bold_n) != 0:  # Kalınların üstüne çizme
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            x += grid

        y = top
        while y <= rect.bottom():
            if y % (grid * bold_n) != 0:
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
            y += grid

        # Kalın çizgiler
        pen_bold = QPen(QColor(COLORS["grid_line_bold"]), 1.0)
        painter.setPen(pen_bold)

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



    # ── Node İşlemleri ───────────────────────────────────────────

    def add_node(
        self,
        instance_id: str,
        descriptor: NodeDescriptor,
        position: QPointF | None = None,
        config: dict | None = None,
    ) -> NodeItem:
        """Sahneye node ekle."""
        node = NodeItem(instance_id, descriptor, config)
        if position:
            node.setPos(position)
        self.addItem(node)
        self._nodes[instance_id] = node
        self.node_added.emit(instance_id, descriptor.node_id)
        return node

    def remove_node(self, instance_id: str) -> None:
        """Node'u ve bağlantılarını sil."""
        node = self._nodes.get(instance_id)
        if node is None:
            return

        # İlişkili edge'leri sil
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

    # ── Edge İşlemleri ───────────────────────────────────────────

    def add_edge_between(
        self,
        source_node_id: str,
        source_port_name: str,
        target_node_id: str,
        target_port_name: str,
    ) -> EdgeItem | None:
        """İki node portu arasında kenar ekle (programmatik)."""
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
        self.edge_added.emit(
            source_node_id, source_port_name,
            target_node_id, target_port_name,
        )
        return edge

    def remove_edge(self, edge: EdgeItem) -> None:
        """Edge'i sahneden sil."""
        edge.disconnect_ports()
        if edge in self._edges:
            self._edges.remove(edge)
        self.removeItem(edge)
        self.edge_removed.emit()

    # ── Bağlantı Çizim ──────────────────────────────────────────

    def start_edge_drawing(self, port: PortItem) -> None:
        """Porttan bağlantı çizmeye başla."""
        self._drawing_source_port = port
        self._drawing_edge = EdgeItem(source_port=port, target_port=None)
        self.addItem(self._drawing_edge)

    def update_edge_drawing(self, scene_pos: QPointF) -> None:
        """Çizim sırasında preview çizgisini güncelle."""
        if self._drawing_edge:
            self._drawing_edge.set_preview_end(scene_pos)

    def finish_edge_drawing(self, target_port: PortItem | None) -> bool:
        """Bağlantı çizimini bitir."""
        if self._drawing_edge is None or self._drawing_source_port is None:
            return False

        success = False

        if target_port is not None and target_port is not self._drawing_source_port:
            # Port uyumu kontrol et
            src = self._drawing_source_port
            tgt = target_port

            # Output → Input yönünde mi?
            if src.is_output and not tgt.is_output:
                if check_port_compatibility(src.port_def.port_type, tgt.port_def.port_type):
                    self._drawing_edge.complete_connection(tgt)
                    self._edges.append(self._drawing_edge)

                    # Sinyal
                    src_node = self._find_node_for_port(src)
                    tgt_node = self._find_node_for_port(tgt)
                    if src_node and tgt_node:
                        self.edge_added.emit(
                            src_node.instance_id, src.port_def.name,
                            tgt_node.instance_id, tgt.port_def.name,
                        )
                    success = True

            elif not src.is_output and tgt.is_output:
                # Ters yön: input'tan output'a çizilmiş — yer değiştir
                if check_port_compatibility(tgt.port_def.port_type, src.port_def.port_type):
                    # Edge'i yeniden oluştur doğru yönde
                    self.removeItem(self._drawing_edge)
                    edge = EdgeItem(tgt, src)
                    self.addItem(edge)
                    self._edges.append(edge)

                    src_node = self._find_node_for_port(tgt)
                    tgt_node = self._find_node_for_port(src)
                    if src_node and tgt_node:
                        self.edge_added.emit(
                            src_node.instance_id, tgt.port_def.name,
                            tgt_node.instance_id, src.port_def.name,
                        )
                    success = True

        if not success:
            # İptal — preview edge'i sil
            self.removeItem(self._drawing_edge)

        self._drawing_edge = None
        self._drawing_source_port = None
        return success

    def cancel_edge_drawing(self) -> None:
        """Bağlantı çizimini iptal et (Esc)."""
        if self._drawing_edge:
            self.removeItem(self._drawing_edge)
            self._drawing_edge = None
            self._drawing_source_port = None

    @property
    def is_drawing_edge(self) -> bool:
        return self._drawing_edge is not None

    # ── Seçim ────────────────────────────────────────────────────

    def get_selected_nodes(self) -> list[NodeItem]:
        return [
            item for item in self.selectedItems()
            if isinstance(item, NodeItem)
        ]

    def get_selected_edges(self) -> list[EdgeItem]:
        return [
            item for item in self.selectedItems()
            if isinstance(item, EdgeItem)
        ]

    def delete_selected(self) -> None:
        """Seçili node ve edge'leri sil."""
        for edge in self.get_selected_edges():
            self.remove_edge(edge)
        for node in self.get_selected_nodes():
            self.remove_node(node.instance_id)

    # ── Temizlik ─────────────────────────────────────────────────

    def clear_all(self) -> None:
        """Tüm node ve edge'leri sil."""
        for edge in list(self._edges):
            self.remove_edge(edge)
        for nid in list(self._nodes.keys()):
            self.remove_node(nid)

    # ── Yardımcılar ──────────────────────────────────────────────

    def _find_node_for_port(self, port: PortItem) -> NodeItem | None:
        """Port'un ait olduğu node'u bul."""
        for node in self._nodes.values():
            if port in node.input_ports or port in node.output_ports:
                return node
        return None

    # ── Mouse olayları ───────────────────────────────────────────

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())

        if isinstance(item, PortItem) and event.button() == Qt.MouseButton.LeftButton:
            self.start_edge_drawing(item)
            return

        super().mousePressEvent(event)

        # Seçim değişikliği bildir
        selected = self.get_selected_nodes()
        if len(selected) == 1:
            self.node_selected.emit(selected[0].instance_id)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.is_drawing_edge:
            self.update_edge_drawing(event.scenePos())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.is_drawing_edge and event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())
            target = item if isinstance(item, PortItem) else None
            self.finish_edge_drawing(target)
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else QTransform())
        if isinstance(item, NodeItem):
            self.node_double_clicked.emit(item.instance_id)
            return
        # Boş alana çift tık — view reset (view tarafında handle edilir)
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_edge_drawing()
            return
        super().keyPressEvent(event)

    # ── Sağ Tık Context Menu ─────────────────────────────────────

    def contextMenuEvent(self, event) -> None:
        """Altium benzeri sağ tık menüsü."""
        pos = event.scenePos()
        transform = self.views()[0].transform() if self.views() else QTransform()
        item = self.itemAt(pos, transform)

        menu = QMenu()
        menu.setStyleSheet(
            f"QMenu {{ background: {COLORS['bg_secondary']}; "
            f"color: {COLORS['text_primary']}; border: 1px solid {COLORS['border_default']}; }}"
            f"QMenu::item:selected {{ background: {COLORS['bg_elevated']}; }}"
        )

        # Node'a tıklandıysa → node menüsü
        node = None
        if isinstance(item, NodeItem):
            node = item
        elif isinstance(item, PortItem) and item.parentItem():
            node = item.parentItem()

        if node is not None and isinstance(node, NodeItem):
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
            for port in node.input_ports + node.output_ports:
                for edge in list(port.connected_edges):
                    self.remove_edge(edge)
        elif chosen == act_delete:
            self.remove_node(node.instance_id)

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
            self._context_add_pos = drop_pos
            self.context_add_requested.emit(node_type_id, drop_pos)
        elif chosen == act_select_all:
            for it in self.items():
                it.setSelected(True)
        elif chosen == act_fit:
            for v in self.views():
                if isinstance(v, QGraphicsView):
                    v_rect = self.itemsBoundingRect()
                    if not v_rect.isEmpty():
                        v.fitInView(v_rect.adjusted(-50, -50, 50, 50),
                                    Qt.AspectRatioMode.KeepAspectRatio)
        elif chosen == act_reset:
            for v in self.views():
                if isinstance(v, QGraphicsView):
                    v.resetTransform()
                    v.centerOn(0, 0)
