"""
Palette — Kategorili blok paleti widget.

Blok ekleme: sürükle-bırak veya çift tık.
Arama filtresi destekli.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QMimeData, QByteArray, Signal
from PySide6.QtGui import QDrag, QColor, QFont
from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QLabel,
    QFrame,
)

from ehapp.theme.tokens import COLORS, FONTS, SIZES
from ehapp.strings.tr import PALETTE_TITLE, PALETTE_SEARCH
from ehcore.registry import NodeRegistry

_MIME_NODE_TYPE = "application/x-eh-node-type"


class _DragTree(QTreeWidget):
    """Sürükle-bırak destekli özel ağaç widget."""

    def startDrag(self, supportedActions) -> None:
        item = self.currentItem()
        if item is None:
            return
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if node_id is None:
            return  # Kategori satırı, sürüklenemeyen

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_MIME_NODE_TYPE, QByteArray(node_id.encode("utf-8")))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class BlockPalette(QWidget):
    """Kategorili blok paleti — arama ve sürükle-bırak destekli."""

    # Çift tık ile ekleme sinyali
    block_double_clicked = Signal(str)  # node_type_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(SIZES["palette_width"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Başlık artık DockWidget tarafından sağlandığı için silindi.

        # Arama
        self._search = QLineEdit()
        self._search.setPlaceholderText(PALETTE_SEARCH)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_blocks)
        layout.addWidget(self._search)

        # Ağaç görünümü — özel DragTree
        self._tree = _DragTree()
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setDragEnabled(True)
        self._tree.setDragDropMode(QTreeWidget.DragDropMode.DragOnly)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._tree)

        # Blokları yükle
        self.reload_blocks()

    def reload_blocks(self) -> None:
        """Registry'den blokları yeniden yükle."""
        self._tree.clear()
        categories = NodeRegistry.get_categories()

        # Kategori ikonları (Modern Text Unicode)
        ICON_MAP = {
            "Kaynaklar": "📡",
            "Ön İşleme": "🔬",
            "Tespit": "🎯",
            "Sınıflandırma": "🧬",
            "İzleme": "📍",
            "Görüntüleyiciler": "🖥️",
            "İşleyiciler": "⚙️",
            "Matematik": "🧮",
            "Mantık": "💡",
            "Metin": "📝",
            "Zaman": "⏰",
            "Dosya": "📁",
            "Veri": "📊",
            "Akış Kontrolü": "🚦",
            "Diğer": "📦",
        }

        for cat_name, descriptors in sorted(categories.items()):
            icon = ICON_MAP.get(cat_name, "▪️")
            display_name = f"{icon}  {cat_name}"
            
            cat_item = QTreeWidgetItem([display_name])
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            font = QFont(FONTS["family"], FONTS["size_sm"])
            font.setWeight(QFont.Weight.Medium)
            cat_item.setFont(0, font)
            cat_item.setForeground(0, QColor(COLORS["text_accent"]))

            for desc in descriptors:
                block_display = f"   {desc.display_name}"
                block_item = QTreeWidgetItem([block_display])
                block_item.setData(0, Qt.ItemDataRole.UserRole, desc.node_id)
                block_item.setToolTip(0, desc.description)
                block_item.setForeground(0, QColor(COLORS["text_primary"]))
                cat_item.addChild(block_item)

            self._tree.addTopLevelItem(cat_item)
            cat_item.setExpanded(True)

    def _filter_blocks(self, text: str) -> None:
        """Arama filtresi."""
        text_lower = text.lower()
        for i in range(self._tree.topLevelItemCount()):
            cat = self._tree.topLevelItem(i)
            any_visible = False
            for j in range(cat.childCount()):
                child = cat.child(j)
                visible = text_lower in child.text(0).lower()
                child.setHidden(not visible)
                if visible:
                    any_visible = True
            cat.setHidden(not any_visible)
            if any_visible:
                cat.setExpanded(True)

    def _on_double_click(self, item: QTreeWidgetItem, column: int) -> None:
        """Çift tık ile blok ekleme."""
        node_id = item.data(0, Qt.ItemDataRole.UserRole)
        if node_id:
            self.block_double_clicked.emit(node_id)
