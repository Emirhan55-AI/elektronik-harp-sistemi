"""
Palette - kategorili blok paleti widget.

Blok ekleme: surukle-birak veya cift tik.
Arama filtresi destekli.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QMimeData, Qt, Signal
from PySide6.QtGui import QDrag, QColor, QFont
from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ehapp.strings import tr
from ehapp.theme.tokens import COLORS, FONTS, SIZES
from ehcore.registry import NodeRegistry

_MIME_NODE_TYPE = "application/x-eh-node-type"

_CATEGORY_TAGS = {
    "kaynaklar": "SRC",
    "on_isleme": "DSP",
    "tespit": "DET",
    "siniflandirma": "CLS",
    "izleme": "TRK",
    "goruntuleyiciler": "VIS",
    "isleyiciler": "DSP",
}


class _DragTree(QTreeWidget):
    """Surukle-birak destekli ozel agac widget."""

    def startDrag(self, supportedActions) -> None:
        del supportedActions
        item = self.currentItem()
        if item is None:
            return
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if node_id is None:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_MIME_NODE_TYPE, QByteArray(node_id.encode("utf-8")))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class BlockPalette(QWidget):
    """Kategorili blok paleti."""

    block_double_clicked = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(SIZES["palette_width"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._search = QLineEdit()
        self._search.setPlaceholderText(tr.PALETTE_SEARCH)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_blocks)
        layout.addWidget(self._search)

        self._tree = _DragTree()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setDragEnabled(True)
        self._tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._tree)

        self.reload_blocks()

    def reload_blocks(self) -> None:
        self._tree.clear()
        categories = NodeRegistry.get_categories()

        for cat_name, descriptors in sorted(categories.items()):
            cat_item = QTreeWidgetItem([self._format_category_name(cat_name)])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            font = QFont(FONTS["family"], FONTS["size_sm"])
            font.setWeight(QFont.Weight.Medium)
            cat_item.setFont(0, font)
            cat_item.setForeground(0, QColor(COLORS["text_accent"]))

            for desc in descriptors:
                block_item = QTreeWidgetItem([f"  {desc.display_name}"])
                block_item.setData(0, Qt.ItemDataRole.UserRole, desc.node_id)
                block_item.setToolTip(0, desc.description)
                block_item.setForeground(0, QColor(COLORS["text_primary"]))
                cat_item.addChild(block_item)

            self._tree.addTopLevelItem(cat_item)
            cat_item.setExpanded(True)

    def _filter_blocks(self, text: str) -> None:
        text_lower = text.lower()
        for index in range(self._tree.topLevelItemCount()):
            cat_item = self._tree.topLevelItem(index)
            any_visible = False
            for child_index in range(cat_item.childCount()):
                child = cat_item.child(child_index)
                visible = text_lower in child.text(0).lower()
                child.setHidden(not visible)
                if visible:
                    any_visible = True
            cat_item.setHidden(not any_visible)
            if any_visible:
                cat_item.setExpanded(True)

    def _on_double_click(self, item: QTreeWidgetItem, column: int) -> None:
        del column
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if node_id:
            self.block_double_clicked.emit(node_id)

    @staticmethod
    def _format_category_name(category_name: str) -> str:
        normalized = (
            category_name.lower()
            .replace("ı", "i")
            .replace("ş", "s")
            .replace("ğ", "g")
            .replace("ü", "u")
            .replace("ö", "o")
            .replace("ç", "c")
            .replace(" ", "_")
        )
        tag = _CATEGORY_TAGS.get(normalized, "BLK")
        return f"[{tag}] {category_name}"
