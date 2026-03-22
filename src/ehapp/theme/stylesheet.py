"""
Stylesheet — Token'lardan QSS string üretimi.

Token'ları alıp platform-uyumlu Qt Style Sheet üretir.
Tüm widget'lar bu stylesheet'i kullanır.
"""

from .tokens import COLORS, FONTS, SIZES


def build_stylesheet() -> str:
    """Ana QSS stylesheet'ini üret."""
    c = COLORS
    f = FONTS
    s = SIZES

    return f"""
    /* ═══════ GLOBAL ═══════ */

    QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: "{f['family']}";
        font-size: {f['size_md']}px;
    }}

    /* ═══════ MENÜ BAR ═══════ */

    QMenuBar {{
        background-color: {c['menubar_bg']};
        color: {c['text_primary']};
        border-bottom: 1px solid {c['border_default']};
        padding: 2px;
        font-size: {f['size_md']}px;
    }}

    QMenuBar::item {{
        padding: 4px 10px;
        border-radius: {s['radius_sm']}px;
    }}

    QMenuBar::item:selected {{
        background-color: {c['bg_elevated']};
    }}

    QMenu {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 24px;
        border-radius: {s['radius_sm']}px;
    }}

    QMenu::item:selected {{
        background-color: {c['bg_elevated']};
        color: {c['accent_primary']};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {c['border_default']};
        margin: 4px 8px;
    }}

    /* ═══════ TOOLBAR ═══════ */

    QToolBar {{
        background-color: {c['toolbar_bg']};
        border-bottom: 1px solid {c['border_default']};
        padding: 2px;
        spacing: 4px;
    }}

    QToolButton {{
        background-color: transparent;
        color: {c['text_primary']};
        border: 1px solid transparent;
        border-radius: {s['radius_md']}px;
        padding: 5px 12px;
        font-size: {f['size_sm']}px;
        font-weight: {f['weight_medium']};
    }}

    QToolButton:hover {{
        background-color: {c['bg_elevated']};
        border-color: {c['border_default']};
    }}

    QToolButton:pressed {{
        background-color: {c['accent_pressed']};
    }}

    /* ═══════ TAB WIDGET ═══════ */

    QTabWidget::pane {{
        border: 1px solid {c['border_default']};
        background-color: {c['bg_secondary']};
    }}

    QTabBar::tab {{
        background-color: {c['tab_inactive']};
        color: {c['text_secondary']};
        border: 1px solid {c['border_default']};
        border-bottom: none;
        padding: 8px 18px;
        margin-right: 2px;
        border-top-left-radius: {s['radius_md']}px;
        border-top-right-radius: {s['radius_md']}px;
        font-weight: {f['weight_medium']};
    }}

    QTabBar::tab:selected {{
        background-color: {c['tab_active']};
        color: {c['accent_primary']};
        border-bottom: 2px solid {c['accent_primary']};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {c['tab_hover']};
        color: {c['text_primary']};
    }}

    /* ═══════ SCROLL BAR ═══════ */

    QScrollBar:vertical {{
        background-color: {c['bg_primary']};
        width: 10px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c['border_default']};
        border-radius: 4px;
        min-height: 30px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c['accent_secondary']};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background-color: {c['bg_primary']};
        height: 10px;
        margin: 0;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c['border_default']};
        border-radius: 4px;
        min-width: 30px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {c['accent_secondary']};
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ═══════ SPLITTER ═══════ */

    QSplitter::handle {{
        background-color: {c['border_default']};
    }}

    QSplitter::handle:horizontal {{
        width: 2px;
    }}

    QSplitter::handle:vertical {{
        height: 2px;
    }}

    /* ═══════ GROUP BOX ═══════ */

    QGroupBox {{
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: {f['weight_medium']};
    }}

    QGroupBox::title {{
        color: {c['text_accent']};
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}

    /* ═══════ INPUT ═══════ */

    QLineEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_sm']}px;
        padding: 5px 8px;
        selection-background-color: {c['accent_secondary']};
    }}

    QLineEdit:focus {{
        border-color: {c['border_focus']};
    }}

    QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_sm']}px;
        padding: 4px 6px;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {c['border_focus']};
    }}

    QComboBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_sm']}px;
        padding: 4px 8px;
    }}

    QComboBox:hover {{
        border-color: {c['border_accent']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        selection-background-color: {c['bg_elevated']};
    }}

    /* ═══════ PUSH BUTTON ═══════ */

    QPushButton {{
        background-color: {c['bg_tertiary']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
        padding: 6px 16px;
        font-weight: {f['weight_medium']};
    }}

    QPushButton:hover {{
        background-color: {c['bg_elevated']};
        border-color: {c['accent_secondary']};
    }}

    QPushButton:pressed {{
        background-color: {c['accent_pressed']};
    }}

    /* ═══════ LABEL ═══════ */

    QLabel {{
        color: {c['text_primary']};
        background-color: transparent;
    }}

    /* ═══════ STATUS BAR ═══════ */

    QStatusBar {{
        background-color: {c['statusbar_bg']};
        color: {c['text_secondary']};
        border-top: 1px solid {c['border_default']};
        font-size: {f['size_xs']}px;
    }}

    /* ═══════ TREE / LIST WIDGET ═══════ */

    QTreeWidget, QListWidget, QTableWidget {{
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_sm']}px;
        alternate-background-color: {c['bg_tertiary']};
    }}

    QTreeWidget::item:selected,
    QListWidget::item:selected,
    QTableWidget::item:selected {{
        background-color: {c['bg_elevated']};
        color: {c['accent_primary']};
    }}

    QTreeWidget::item:hover,
    QListWidget::item:hover {{
        background-color: {c['bg_tertiary']};
    }}

    QHeaderView::section {{
        background-color: {c['bg_tertiary']};
        color: {c['text_secondary']};
        border: 1px solid {c['border_default']};
        padding: 4px 8px;
        font-weight: {f['weight_medium']};
    }}

    /* ═══════ TEXT EDIT (LOG) ═══════ */

    QTextEdit, QPlainTextEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_sm']}px;
        font-family: "{f['family_mono']}";
        font-size: {f['size_sm']}px;
    }}

    /* ═══════ TOOLTIPS ═══════ */

    QToolTip {{
        background-color: {c['bg_elevated']};
        color: {c['text_primary']};
        border: 1px solid {c['border_accent']};
        border-radius: {s['radius_sm']}px;
        padding: 4px 8px;
        font-size: {f['size_sm']}px;
    }}
    """
