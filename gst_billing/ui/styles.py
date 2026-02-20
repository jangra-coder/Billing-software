"""
QSS stylesheet — light theme (default) with accent-colour system.

Provides get_stylesheet(theme, accent) that returns a full QSS string.
"""

from __future__ import annotations

from pathlib import Path

# Resolve checkbox tick SVG path once (absolute, forward-slash for QSS)
_CHECK_SVG = (Path(__file__).resolve().parent.parent / "assets" / "icons" / "check.svg")
_CHECK_SVG_URL = _CHECK_SVG.as_posix()

# ---------------------------------------------------------------------------
# Colour palettes
# ---------------------------------------------------------------------------
LIGHT = {
    "bg":           "#FFFFFF",
    "bg_alt":       "#F5F5F5",
    "bg_sidebar":   "#2C3E50",
    "fg":           "#212121",
    "fg_muted":     "#757575",
    "fg_sidebar":   "#ECF0F1",
    "border":       "#E0E0E0",
    "input_bg":     "#FFFFFF",
    "input_border": "#BDBDBD",
    "hover":        "#E8EAF6",
    "selected":     "#BBDEFB",
    "danger":       "#E53935",
    "success":      "#43A047",
    "warning":      "#FB8C00",
}

DARK = {
    "bg":           "#1E1E1E",
    "bg_alt":       "#252526",
    "bg_sidebar":   "#1A1A2E",
    "fg":           "#D4D4D4",
    "fg_muted":     "#808080",
    "fg_sidebar":   "#CCD6F6",
    "border":       "#3C3C3C",
    "input_bg":     "#2D2D2D",
    "input_border": "#555555",
    "hover":        "#2A2D2E",
    "selected":     "#094771",
    "danger":       "#CF6679",
    "success":      "#81C784",
    "warning":      "#FFB74D",
}

PALETTES = {"light": LIGHT, "dark": DARK}


def get_stylesheet(theme: str = "light", accent: str = "#1565C0") -> str:
    """Return a complete QSS string for the application."""
    p = PALETTES.get(theme, LIGHT)
    accent_hover = _lighten(accent, 0.15)
    accent_pressed = _darken(accent, 0.10)
    check_svg = _CHECK_SVG_URL

    return f"""
/* ========= Global ========= */
QWidget {{
    font-family: "Helvetica Neue", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: {p["fg"]};
    background-color: {p["bg"]};
}}

/* ========= Main Window ========= */
QMainWindow {{
    background-color: {p["bg"]};
}}

/* ========= Sidebar ========= */
#sidebar {{
    background-color: {p["bg_sidebar"]};
    min-width: 54px;
}}
#sidebar QPushButton {{
    text-align: left;
    padding: 10px 14px;
    border: none;
    border-radius: 0px;
    color: {p["fg_sidebar"]};
    background: transparent;
    font-size: 13px;
    min-height: 18px;
}}
#sidebar QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.10);
}}
#sidebar QPushButton:checked,
#sidebar QPushButton[active="true"] {{
    background-color: {accent};
    color: #FFFFFF;
    font-weight: bold;
}}
#sidebar QLabel#appTitle {{
    color: #FFFFFF;
    font-size: 15px;
    font-weight: bold;
    padding: 16px 14px 10px 14px;
}}
#sidebar QFrame#separator {{
    background-color: rgba(255,255,255,0.12);
    max-height: 1px;
    margin: 4px 10px;
}}
#sidebar QPushButton#sidebarToggle {{
    text-align: center;
    padding: 6px 10px;
    font-size: 12px;
    color: rgba(255,255,255,0.55);
    background: transparent;
    border-top: 1px solid rgba(255,255,255,0.08);
    border-radius: 0;
}}
#sidebar QPushButton#sidebarToggle:hover {{
    color: #FFFFFF;
    background-color: rgba(255,255,255,0.08);
}}

/* ========= Push Button ========= */
QPushButton {{
    background-color: {accent};
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 7px 18px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {accent_hover};
}}
QPushButton:pressed {{
    background-color: {accent_pressed};
}}
QPushButton:disabled {{
    background-color: {p["border"]};
    color: {p["fg_muted"]};
}}
QPushButton[flat="true"],
QPushButton#flatBtn {{
    background: transparent;
    color: {accent};
    border: 1px solid {accent};
}}
QPushButton[flat="true"]:hover,
QPushButton#flatBtn:hover {{
    background-color: {p["hover"]};
}}
QPushButton[danger="true"] {{
    background-color: {p["danger"]};
}}
QPushButton[secondary="true"] {{
    background-color: {p["bg_alt"]};
    color: {p["fg"]};
    border: 1px solid {p["border"]};
}}
QPushButton[secondary="true"]:hover {{
    background-color: {p["hover"]};
}}

/* ========= Line Edit / Text Edit ========= */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {p["input_bg"]};
    border: 1px solid {p["input_border"]};
    border-radius: 4px;
    padding: 6px 10px;
    min-height: 20px;
    selection-background-color: {accent};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {accent};
}}
QLineEdit:disabled, QLineEdit:read-only {{
    background-color: {p["bg_alt"]};
    color: {p["fg_muted"]};
}}

/* ========= Combo Box ========= */
QComboBox {{
    background-color: {p["input_bg"]};
    border: 1px solid {p["input_border"]};
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 24px;
}}
QComboBox:focus {{
    border: 1.5px solid {accent};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid {p["input_border"]};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {p["input_bg"]};
    border: 1px solid {p["border"]};
    selection-background-color: {p["selected"]};
    padding: 4px 0;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 26px;
    padding: 4px 8px;
}}

/* ========= Spin Box ========= */
QSpinBox, QDoubleSpinBox {{
    background-color: {p["input_bg"]};
    border: 1px solid {p["input_border"]};
    border-radius: 4px;
    padding: 5px 8px;
    min-height: 24px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1.5px solid {accent};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid {p["input_border"]};
    border-top-right-radius: 4px;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border-left: 1px solid {p["input_border"]};
    border-bottom-right-radius: 4px;
}}

/* ========= Table — modern look ========= */
QTableWidget, QTableView {{
    gridline-color: {p["border"]};
    background-color: {p["bg"]};
    alternate-background-color: {p["bg_alt"]};
    selection-background-color: {p["selected"]};
    border: 1px solid {p["border"]};
    border-radius: 6px;
    font-size: 13px;
    outline: none;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {p["border"]};
}}
QTableWidget::item:selected {{
    background-color: {p["selected"]};
    color: {p["fg"]};
}}
QTableWidget QLineEdit {{
    padding: 4px 6px;
    margin: 1px;
    min-height: 18px;
    border: 1.5px solid {accent};
    border-radius: 2px;
}}
QHeaderView {{
    background-color: transparent;
}}
QHeaderView::section {{
    background-color: {p["bg_alt"]};
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid {accent};
    font-weight: 600;
    font-size: 12px;
    color: {p["fg"]};
    min-height: 20px;
}}
QHeaderView::section:horizontal:last {{
    border-right: none;
}}

/* ========= Tab Widget ========= */
QTabWidget::pane {{
    border: 1px solid {p["border"]};
    border-top: none;
    background-color: {p["bg"]};
    border-radius: 0 0 6px 6px;
}}
QTabBar::tab {{
    background-color: {p["bg_alt"]};
    padding: 10px 24px;
    border: 1px solid {p["border"]};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-size: 13px;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    background-color: {p["bg"]};
    border-bottom: 2px solid {accent};
    font-weight: bold;
    color: {accent};
}}
QTabBar::tab:hover:!selected {{
    background-color: {p["hover"]};
}}

/* ========= Form Layout ========= */
QFormLayout {{
    margin: 0;
}}

/* ========= Scroll Bar ========= */
QScrollBar:vertical {{
    background: {p["bg_alt"]};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {p["border"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p["fg_muted"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {p["bg_alt"]};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {p["border"]};
    border-radius: 4px;
    min-width: 30px;
}}

/* ========= Group Box ========= */
QGroupBox {{
    font-weight: bold;
    border: 1px solid {p["border"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 20px 16px 14px 16px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
    color: {accent};
    font-size: 13px;
}}

/* ========= Scroll Area ========= */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: {p["bg"]};
}}

/* ========= Dialog ========= */
QDialog {{
    background-color: {p["bg"]};
}}

/* ========= Status bar / Labels ========= */
QStatusBar {{
    background-color: {p["bg_alt"]};
    border-top: 1px solid {p["border"]};
    font-size: 12px;
}}
QLabel#heading {{
    font-size: 20px;
    font-weight: bold;
    color: {p["fg"]};
    padding: 2px 0;
}}
QLabel#subheading {{
    font-size: 14px;
    color: {p["fg_muted"]};
}}
QLabel#sectionTitle {{
    font-size: 14px;
    font-weight: bold;
    color: {accent};
    padding: 4px 0;
}}
QLabel#errorLabel {{
    color: {p["danger"]};
    font-weight: bold;
}}
QLabel#successLabel {{
    color: {p["success"]};
    font-weight: bold;
}}
QLabel#metricValue {{
    font-size: 22px;
    font-weight: bold;
    color: {accent};
}}
QLabel#metricLabel {{
    font-size: 11px;
    color: {p["fg_muted"]};
    text-transform: uppercase;
}}

/* ========= Card-style container ========= */
#card {{
    background-color: {p["bg"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    padding: 16px;
}}

/* ========= Toolbar row ========= */
#toolbar {{
    background-color: {p["bg_alt"]};
    border: 1px solid {p["border"]};
    border-radius: 6px;
    padding: 8px 12px;
    margin: 4px 0;
}}

/* ========= Placeholder pages ========= */
#placeholderPage {{
    background-color: {p["bg"]};
}}
#placeholderPage QLabel {{
    color: {p["fg_muted"]};
    font-size: 16px;
}}

/* ========= Wizard ========= */
#wizardPage {{
    background-color: {p["bg"]};
}}

/* ========= Totals Panel ========= */
#totalsPanel {{
    background-color: {p["bg_alt"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    padding: 14px;
}}

/* ========= Check Box — classic tick mark ========= */
QCheckBox {{
    spacing: 8px;
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {p["input_border"]};
    border-radius: 3px;
    background: {p["input_bg"]};
}}
QCheckBox::indicator:hover {{
    border-color: {accent};
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
    image: url("{check_svg}");
}}

/* ========= Splitter handle ========= */
QSplitter::handle {{
    background-color: {p["border"]};
    width: 2px;
}}
QSplitter::handle:hover {{
    background-color: {accent};
}}

/* ========= Date Edit ========= */
QDateEdit {{
    background-color: {p["input_bg"]};
    border: 1px solid {p["input_border"]};
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 24px;
}}
QDateEdit:focus {{
    border: 1.5px solid {accent};
}}
QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid {p["input_border"]};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}}

/* ========= QCalendarWidget popup ========= */
QCalendarWidget QAbstractItemView {{
    selection-background-color: {accent};
    selection-color: #FFFFFF;
}}

/* ========= Message Box ========= */
QMessageBox {{
    background-color: {p["bg"]};
}}
QMessageBox QLabel {{
    font-size: 13px;
    min-width: 300px;
}}
"""


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _lighten(hex_color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return _rgb_to_hex(r, g, b)


def _darken(hex_color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return _rgb_to_hex(r, g, b)
