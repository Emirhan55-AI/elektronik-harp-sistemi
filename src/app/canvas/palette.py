"""Kategorili blok paleti."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QMimeData, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont
from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from app.strings import tr
from app.theme.tokens import COLORS, FONTS, SIZES
from ehplatform.registry import NodeRegistry

_MIME_NODE_TYPE = "application/x-eh-node-type"

_CATEGORY_LABELS = {
    "kaynaklar": tr.CAT_SOURCES,
    "on_isleme": tr.CAT_PROCESSORS,
    "tespit": tr.CAT_DETECTORS,
    "siniflandirma": tr.CAT_CLASSIFIERS,
    "izleme": tr.CAT_TRACKING,
    "goruntuleyiciler": tr.CAT_VIEWERS,
    "isleyiciler": tr.CAT_PROCESSORS,
}


class _DragTree(QTreeWidget):
    """Sürükle-bırak destekli ağaç."""

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
        self.setObjectName("PaletteRoot")
        self.setFixedWidth(SIZES["palette_width"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._search = QLineEdit()
        self._search.setObjectName("PaletteSearch")
        self._search.setPlaceholderText(tr.PALETTE_SEARCH)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_blocks)
        layout.addWidget(self._search)

        self._tree = _DragTree()
        self._tree.setObjectName("PaletteTree")
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setDragEnabled(True)
        self._tree.setIndentation(14)
        self._tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._tree)

        self.reload_blocks()

    def reload_blocks(self) -> None:
        self._tree.clear()
        categories = NodeRegistry.get_categories()

        for category_name, descriptors in sorted(categories.items()):
            category_item = QTreeWidgetItem([self._format_category_name(category_name)])
            category_item.setFlags(category_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            font = QFont(FONTS["family"], max(1, int(FONTS["size_sm"])))
            font.setWeight(QFont.Weight.Medium)
            category_item.setFont(0, font)
            category_item.setForeground(0, QColor(COLORS["text_accent"]))

            for descriptor in descriptors:
                block_item = QTreeWidgetItem([f"  {descriptor.display_name}"])
                block_item.setData(0, Qt.ItemDataRole.UserRole, descriptor.node_id)
                block_item.setToolTip(0, descriptor.description)
                block_item.setForeground(0, QColor(COLORS["text_primary"]))
                category_item.addChild(block_item)

            self._tree.addTopLevelItem(category_item)
            category_item.setExpanded(True)

    def _filter_blocks(self, text: str) -> None:
        needle = text.casefold()
        for index in range(self._tree.topLevelItemCount()):
            category_item = self._tree.topLevelItem(index)
            category_visible = False
            for child_index in range(category_item.childCount()):
                child = category_item.child(child_index)
                visible = needle in child.text(0).casefold()
                child.setHidden(not visible)
                if visible:
                    category_visible = True
            category_item.setHidden(not category_visible)
            if category_visible:
                category_item.setExpanded(True)

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
        return _CATEGORY_LABELS.get(normalized, category_name)
