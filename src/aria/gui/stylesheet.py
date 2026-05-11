# noqa: E501
"""Global stylesheet for the Aria GUI application.

Colour palette aligned with the Chainlit WebUI light theme (public/theme.json).
Design tokens:
    Primary     : #008457  (green, hsl 155 100% 26%)
    Background  : #F7F5F0  (warm off-white, hsl 45 18% 96%)
    Card        : #FBFAF7  (warm white, hsl 48 16% 98%)
    Border      : #C9C5BB  (warm gray, hsl 40 10% 78%)
    Text        : #111318  (near-black, hsl 210 6% 7%)
    Muted text  : #62666B  (warm gray, hsl 210 4% 40%)
    Accent      : #D8EDE4  (light green, hsl 155 32% 91%)
    Destructive : #E53E3E  (hsl 0 84% 60%)
    Font        : Geist Sans / Geist Mono (loaded via CSS in the WebUI)
"""

STYLESHEET = """
/* ============================================================
   Aria GUI — Global Stylesheet (WebUI Light-Theme Palette)
   ============================================================ */

/* --- Base & Window --- */

QWidget {
    font-size: 12px;
    color: #111318;
    background-color: #F7F5F0;
}

QMainWindow {
    background-color: #F7F5F0;
}

QMainWindow::separator {
    background: #C9C5BB;
    width: 1px;
    height: 1px;
}

/* --- Menu Bar --- */

QMenuBar {
    background-color: #F7F5F0;
    border-bottom: 1px solid #D5D1C8;
    padding: 2px 4px;
}

QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #D8EDE4;
    color: #008457;
}

QMenu {
    background-color: #FBFAF7;
    border: 1px solid #C9C5BB;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #D8EDE4;
    color: #008457;
}

QMenu::separator {
    height: 1px;
    background: #D5D1C8;
    margin: 4px 8px;
}

/* --- Status Bar --- */

QStatusBar {
    background-color: #E8E6E0;
    border-top: 1px solid #D5D1C8;
    color: #62666B;
    font-size: 12px;
    padding: 2px 8px;
}

QStatusBar::item {
    border: none;
}

/* --- Tab Widget --- */

QTabWidget::pane {
    border: 1px solid #C9C5BB;
    border-radius: 8px;
    background-color: #FBFAF7;
    top: -1px;
}

QTabBar {
    background: transparent;
}

QTabBar::tab {
    background-color: #E8E6E0;
    border: 1px solid #C9C5BB;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 20px;
    margin-right: 2px;
    font-weight: 500;
    color: #62666B;
}

QTabBar::tab:selected {
    background-color: #FBFAF7;
    color: #008457;
    border-color: #C9C5BB;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background-color: #D5D1C8;
    color: #111318;
}

/* --- Group Box --- */

QGroupBox {
    font-weight: 600;
    font-size: 13px;
    color: #111318;
    border: 1px solid #C9C5BB;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 20px;
    background-color: #FBFAF7;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
    background-color: #FBFAF7;
    color: #111318;
}

QGroupBox::indicator {
    width: 16px;
    height: 16px;
}

/* --- Frames (transparent inside containers) --- */

QFrame {
    background: transparent;
}

/* --- Push Buttons --- */

QPushButton {
    background-color: #FBFAF7;
    border: 1px solid #C9C5BB;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    color: #111318;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #E8E6E0;
    border-color: #008457;
    color: #008457;
}

QPushButton:pressed {
    background-color: #D5D1C8;
    border-color: #005538;
    color: #005538;
}

QPushButton:disabled {
    background-color: #E8E6E0;
    border-color: #D5D1C8;
    color: #95999E;
}

QPushButton:focus {
    outline: none;
    border-color: #008457;
}

QPushButton[primary="true"] {
    background-color: #008457;
    border-color: #008457;
    color: #FFFFFF;
}

QPushButton[primary="true"]:hover {
    background-color: #006B47;
    border-color: #006B47;
}

QPushButton[primary="true"]:pressed {
    background-color: #005538;
    border-color: #005538;
}

QPushButton[primary="true"]:disabled {
    background-color: #66B899;
    border-color: #66B899;
    color: #FFFFFF;
}

QPushButton[danger="true"] {
    background-color: #FBFAF7;
    border-color: #E53E3E;
    color: #E53E3E;
}

QPushButton[danger="true"]:hover {
    background-color: #FDE8E8;
    border-color: #E53E3E;
    color: #E53E3E;
}

QPushButton[warning="true"] {
    background-color: #FBFAF7;
    border-color: #D97706;
    color: #D97706;
}

QPushButton[warning="true"]:hover {
    background-color: #FEF3C7;
    border-color: #D97706;
    color: #D97706;
}

QPushButton[warning="true"]:disabled {
    background-color: #E8E6E0;
    border-color: #D5D1C8;
    color: #95999E;
}

/* --- Line Edit --- */

QLineEdit {
    background-color: #FBFAF7;
    border: 1px solid #C9C5BB;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #111318;
    selection-background-color: #C8E6D8;
    selection-color: #111318;
    min-width: 200px;
    min-height: 20px;
}

QLineEdit:focus {
    border-color: #008457;
}

QLineEdit:disabled {
    background-color: #E8E6E0;
    color: #95999E;
}

/* --- Spin Box --- */

QSpinBox {
    background-color: #FBFAF7;
    border: 1px solid #C9C5BB;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #111318;
}

QSpinBox:focus {
    border-color: #008457;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: transparent;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #D8EDE4;
}

QSpinBox::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #62666B;
    width: 0;
    height: 0;
}

QSpinBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #62666B;
    width: 0;
    height: 0;
}

/* --- Combo Box --- */

QComboBox {
    background-color: #FBFAF7;
    border: 1px solid #C9C5BB;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #111318;
    min-height: 20px;
}

QComboBox:focus {
    border-color: #008457;
}

QComboBox:hover {
    border-color: #008457;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #62666B;
    width: 0;
    height: 0;
}

QComboBox QAbstractItemView {
    background-color: #FBFAF7;
    border: 1px solid #C9C5BB;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #D8EDE4;
    selection-color: #008457;
    outline: none;
}

QComboBox QAbstractItemView::item {
    padding: 6px 12px;
    border-radius: 4px;
    min-height: 24px;
}

/* --- Check Box --- */

QCheckBox {
    spacing: 8px;
    font-size: 13px;
    color: #111318;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #C9C5BB;
    border-radius: 4px;
    background-color: #FBFAF7;
}

QCheckBox::indicator:hover {
    border-color: #008457;
}

QCheckBox::indicator:checked {
    background-color: #008457;
    border-color: #008457;
    image: url(none);
    /* White checkmark via border trick */
    border: 2px solid #008457;
    border-radius: 4px;
}

QCheckBox::indicator:disabled {
    background-color: #E8E6E0;
    border-color: #D5D1C8;
}

/* --- Radio Button --- */

QRadioButton {
    spacing: 8px;
    font-size: 13px;
    color: #111318;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #C9C5BB;
    border-radius: 9px;
    background-color: #FBFAF7;
}

QRadioButton::indicator:hover {
    border-color: #008457;
}

QRadioButton::indicator:checked {
    background-color: #FBFAF7;
    border: 5px solid #008457;
    border-radius: 9px;
    width: 8px;
    height: 8px;
}

/* --- Plain Text Edit (Log/Output Panes) --- */

QPlainTextEdit {
    background-color: #F3F0EA;
    border: 1px solid #C9C5BB;
    border-radius: 8px;
    padding: 12px;
    font-size: 11px;
    color: #111318;
    selection-background-color: #C8E6D8;
}

QPlainTextEdit:focus {
    border-color: #008457;
}

QPlainTextEdit:disabled {
    background-color: #E8E6E0;
    color: #95999E;
}

/* --- Text Edit (Logs) --- */

QTextEdit {
    background-color: #F3F0EA;
    border: 1px solid #C9C5BB;
    border-radius: 8px;
    padding: 12px;
    font-size: 12px;
    color: #111318;
    selection-background-color: #C8E6D8;
}

QTextEdit:focus {
    border-color: #008457;
}

/* --- List Widget --- */

QListWidget {
    background-color: #FBFAF7;
    border: 1px solid #C9C5BB;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 1px 0;
}

QListWidget::item:selected {
    background-color: #D8EDE4;
    color: #008457;
}

QListWidget::item:hover:!selected {
    background-color: #E8E6E0;
}

/* --- Scroll Area --- */

QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #C9C5BB;
    border-radius: 4px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background: #95999E;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #C9C5BB;
    border-radius: 4px;
    min-width: 32px;
}

QScrollBar::handle:horizontal:hover {
    background: #95999E;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    width: 0;
}

/* --- Labels --- */

QLabel {
    background: transparent;
    color: #111318;
}

/* --- Tooltips --- */

QToolTip {
    background-color: #111318;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}

/* --- Dialog --- */

QDialog {
    background-color: #F7F5F0;
}

/* --- Message Box --- */

QMessageBox {
    background-color: #F7F5F0;
}

/* --- Wizard --- */

QWizard {
    background-color: #F7F5F0;
}

QWizardPage {
    background-color: #F7F5F0;
}

QWizardPage QLineEdit {
    min-width: 280px;
}

QDialog QLineEdit {
    min-width: 250px;
}

/* ============================================================
   Dynamic State Selectors (set via setProperty() in code)
   ============================================================ */

/* Status Badge */
QLabel[status="running"] {
    background-color: #008457;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 12px 4px 28px;
    border-radius: 2px;
    min-width: 90px;
}

QLabel[status="warning"] {
    background-color: #D97706;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 12px 4px 28px;
    border-radius: 2px;
    min-width: 90px;
}

QLabel[status="error"] {
    background-color: #E53E3E;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 12px 4px 28px;
    border-radius: 2px;
    min-width: 90px;
}

QLabel[status="idle"] {
    background-color: #62666B;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 12px 4px 28px;
    border-radius: 2px;
    min-width: 90px;
}

QLabel[status="success"] {
    color: #008457;
    font-weight: 600;
}

/* Password Strength */
QLabel[strength="weak"] {
    color: #E53E3E;
    font-weight: 600;
}

QLabel[strength="fair"] {
    color: #D97706;
    font-weight: 600;
}

QLabel[strength="strong"] {
    color: #008457;
    font-weight: 600;
}

QLabel[strength="none"] {
    color: transparent;
}

/* Muted form labels */
QLabel[muted="true"] {
    color: #62666B;
}

/* Connection status */
QLabel[connection="ok"] {
    color: #008457;
}

QLabel[connection="fail"] {
    color: #E53E3E;
}
"""
