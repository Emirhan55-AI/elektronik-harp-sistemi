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

    QWidget#PaletteRoot,
    QWidget#LogPanelRoot,
    QWidget#InspectorRoot,
    QWidget#SummaryRoot,
    QWidget#EventFeedRoot,
    QWidget#SystemPanelRoot {{
        background-color: {c['bg_secondary']};
    }}

    /* ═══════ MENÜ BAR ═══════ */

    QMenuBar {{
        background-color: {c['menubar_bg']};
        color: white;
        border-bottom: 1px solid {c['border_default']};
        padding: 2px;
        font-size: {f['size_md']}px;
    }}

    QMenuBar::item {{
        background-color: transparent;
        color: white;
        padding: 4px 10px;
        border-radius: {s['radius_sm']}px;
    }}

    QMenuBar::item:selected {{
        background-color: {c['bg_elevated']};
        color: {c['accent_primary']};
    }}

    QMenu {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
        padding: 6px 4px;
    }}

    QMenu::item {{
        padding: 8px 16px 8px 28px;
        margin: 0 2px;
        border-radius: {s['radius_sm']}px;
        background-color: transparent;
    }}

    QMenu::item:selected {{
        background-color: {c['bg_elevated']};
        color: {c['accent_primary']};
    }}

    QMenu::item:checked {{
        color: {c['accent_primary']};
        background-color: {c['bg_elevated']};
    }}

    QMenu::indicator {{
        width: 12px;
        height: 12px;
        left: 8px;
        border-radius: 6px;
        background: transparent;
    }}

    QMenu::indicator:checked {{
        background: {c['accent_primary']};
        border: 1px solid {c['accent_primary']};
    }}

    QMenu::indicator:unchecked {{
        background: transparent;
        border: 1px solid transparent;
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {c['border_default']};
        margin: 4px 8px;
    }}

    /* ═══════ TOOLBAR ═══════ */

    QToolBar {{
        background-color: {c['toolbar_bg']};
        border-bottom: none;
        padding: 5px 10px 6px 10px;
        spacing: 0px;
    }}

    QToolBar#MainToolbar {{
        background-color: {c['toolbar_bg']};
        border-bottom: none;
    }}

    QWidget#ToolbarHost {{
        background-color: {c['toolbar_bg']};
        border: none;
    }}

    QToolBar::separator {{
        background: transparent;
        width: 0px;
        margin: 0;
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

    QDockWidget {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border_default']};
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}

    QDockWidget::title {{
        text-align: left;
        background-color: {c['bg_secondary']};
        color: {c['text_primary']};
        padding: 8px 10px;
        border-bottom: 1px solid {c['border_default']};
        font-size: {f['size_md']}px;
        font-weight: {f['weight_medium']};
    }}

    QMainWindow::separator {{
        background-color: {c['border_default']};
        width: 1px;
        height: 1px;
        margin: 0;
    }}

    QMainWindow::separator:hover {{
        background-color: {c['accent_secondary']};
    }}

    /* ═══════ TAB WIDGET ═══════ */

    QTabWidget::pane {{
        border: 1px solid {c['border_default']};
        background-color: {c['bg_secondary']};
        top: -1px;
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

    QLineEdit#PaletteSearch {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
        padding: 7px 10px;
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
        selection-background-color: {c['state_selected_bg']};
        selection-color: {c['state_selected']};
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

    QPushButton#PrimaryButton {{
        background-color: {c['accent_primary']};
        color: {c['bg_primary']};
        border-color: {c['accent_primary']};
        font-weight: {f['weight_bold']};
    }}

    QPushButton#PrimaryButton:hover {{
        background-color: {c['accent_hover']};
        border-color: {c['accent_hover']};
    }}

    QToolButton#ActionButton {{
        background-color: {c['bg_tertiary']};
        color: white;
        border: 1px solid {c['border_default']};
        border-radius: 6px;
        padding: 4px 10px;
        min-width: 40px;
        height: 32px;
        margin: 0px 2px;
        icon-size: 16px;
    }}

    QToolButton#ActionButton:hover {{
        background-color: {c['bg_elevated']};
        border-color: {c['accent_primary']};
        color: {c['accent_hover']};
    }}

    QToolButton#ActionButton:pressed {{
        background-color: {c['accent_pressed']};
        color: {c['bg_primary']};
    }}

    QToolButton#ActionButton[running="true"] {{
        background-color: {c['error']};
        color: white;
        border-color: {c['error']};
    }}

    QToolButton#ActionButton::menu-button {{
        width: 0px;
        border: none;
    }}

    QToolButton#ActionButton::menu-indicator {{
        image: none;
        width: 0px;
    }}

    QPushButton#ModeToggle {{
        background-color: {c['bg_tertiary']};
        color: {c['text_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: 0px;
        padding: 0px 16px;
        height: 32px;
        min-width: 100px;
        margin: 0px -1px 0px 0px;
        font-size: {f['size_sm']}px;
        font-weight: {f['weight_medium']};
    }}

    QPushButton#ModeToggle:first-child {{
        border-top-left-radius: 6px;
        border-bottom-left-radius: 6px;
    }}

    QPushButton#ModeToggle:last-child {{
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
        margin-right: 0px;
    }}

    QPushButton#ModeToggle:hover {{
        background-color: {c['bg_elevated']};
        color: {c['text_primary']};
        z-index: 10;
    }}

    QPushButton#ModeToggle:checked {{
        background-color: {c['bg_elevated']};
        color: {c['accent_primary']};
        border: 1px solid {c['accent_primary']};
        font-weight: {f['weight_bold']};
        z-index: 20;
    }}

    QPushButton#IconButton {{
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        padding: 0;
        background-color: transparent;
        border: 1px solid transparent;
        color: white;
    }}

    QPushButton#IconButton:hover {{
        background-color: {c['bg_elevated']};
        border-color: {c['border_default']};
        color: {c['text_primary']};
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

    QTreeWidget#PaletteTree {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
        padding: 6px;
        outline: 0;
    }}

    QTreeWidget#PaletteTree::item {{
        padding: 4px 8px;
        margin: 1px 0;
        border-radius: {s['radius_sm']}px;
    }}

    QTreeWidget::item:selected,
    QListWidget::item:selected,
    QTableWidget::item:selected {{
        background-color: {c['state_selected_bg']};
        color: {c['state_selected']};
        border-color: {c['state_selected']};
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

    QTextEdit#LogOutput {{
        background-color: {c['bg_input']};
        border: none;
        border-radius: 0;
        margin: 0;
        padding: 6px;
    }}

    QFrame#SystemPanelHeader {{
        background-color: {c['bg_secondary']};
        border-bottom: 1px solid {c['border_default']};
        padding: 0;
        margin: 0;
    }}

    QLabel#SystemPanelTabLabel {{
        background-color: {c['tab_active']};
        color: {c['accent_primary']};
        border-top: 1px solid {c['border_default']};
        border-left: 1px solid {c['border_default']};
        border-right: 1px solid {c['border_default']};
        border-bottom: 2px solid {c['accent_primary']};
        border-top-left-radius: {s['radius_md']}px;
        border-top-right-radius: {s['radius_md']}px;
        padding: 8px 18px;
        margin: 0 0 -1px 0;
        font-weight: {f['weight_medium']};
    }}

    QPushButton#LogClearButton {{
        background-color: {c['bg_secondary']};
        color: {c['text_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_sm']}px;
        padding: 3px 10px;
        margin: 6px 8px 6px 8px;
        font-size: {f['size_xs']}px;
    }}

    QPushButton#LogClearButton:hover {{
        color: {c['text_primary']};
        border-color: {c['accent_secondary']};
        background-color: {c['bg_elevated']};
    }}

    QListWidget#IssuesList {{
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
        background-color: {c['bg_input']};
        padding: 4px;
    }}

    QListWidget#IssuesList::item {{
        padding: 8px 10px;
        margin: 2px 0;
        border-radius: {s['radius_sm']}px;
        border: 1px solid transparent;
    }}

    QListWidget#IssuesList::item:selected {{
        background-color: {c['state_selected_bg']};
        border-color: {c['state_selected']};
    }}

    QListWidget#EventFeedList {{
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
        background-color: {c['bg_input']};
        padding: 4px;
    }}

    QListWidget#EventFeedList::item {{
        padding: 8px 10px;
        margin: 2px 0;
        border-radius: {s['radius_sm']}px;
        border: 1px solid transparent;
    }}

    QListWidget#EventFeedList::item:selected {{
        background-color: {c['state_selected_bg']};
        border-color: {c['state_selected']};
    }}

    QFrame#InspectorCard {{
        background-color: {c['bg_input']};
        border: 1px solid {c['border_default']};
        border-radius: {s['radius_md']}px;
    }}

    QLabel#SectionTitle {{
        color: {c['text_accent']};
        font-size: {f['size_sm']}px;
        font-weight: {f['weight_bold']};
        letter-spacing: 0.5px;
        padding-bottom: 4px;
        border-bottom: 1px solid {c['border_default']};
        margin-bottom: 4px;
    }}

    QLabel#SummaryValue {{
        color: {c['text_primary']};
        font-size: {f['size_md']}px;
        font-weight: {f['weight_medium']};
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


