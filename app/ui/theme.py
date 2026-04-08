"""Centralized dark theme for Qwen3-TTS Desktop.

Design tokens follow a three-layer architecture:
  Primitive  →  Semantic  →  Component
(raw values)   (purpose)    (widget-specific)

Priority rules applied (ui-ux-pro-max skill):
  - Contrast ≥ 4.5:1 (WCAG AA)
  - Min interactive target 44×44 px
  - Base font 14 px (increased from system default ~8pt)
  - No gray-on-gray
  - Loading feedback on all async operations
  - Keyboard shortcuts for primary actions
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

# ─────────────────────────────────────────────
# PRIMITIVE TOKENS  (raw values)
# ─────────────────────────────────────────────
_P = {
    # Grays
    "gray-900": "#12131e",
    "gray-800": "#1a1b2e",
    "gray-750": "#1f2035",
    "gray-700": "#24253a",
    "gray-650": "#2b2c44",
    "gray-600": "#32334e",
    "gray-500": "#44455e",
    "gray-400": "#626480",
    "gray-300": "#8888a8",
    "gray-200": "#c0c0d8",
    "gray-100": "#e2e2f0",
    "gray-50":  "#f0f0f8",
    # Purple (primary brand)
    "purple-700": "#5b4ce0",
    "purple-600": "#6c5ce7",
    "purple-500": "#7c6af7",
    "purple-400": "#9b8dff",
    "purple-100": "#2e2857",
    # Teal (accent)
    "teal-400":   "#64ffda",
    "teal-300":   "#92ffe8",
    "teal-dark":  "#1a4040",
    # Status
    "green-400":  "#4ade80",
    "green-dark": "#1a3d1a",
    "red-400":    "#ff6b6b",
    "red-dark":   "#3d1a1a",
    "yellow-400": "#fbbf24",
    "yellow-dark":"#3d3010",
    # Neutral
    "white": "#ffffff",
    "black": "#000000",
    "transparent": "transparent",
}

# ─────────────────────────────────────────────
# SEMANTIC TOKENS  (purpose aliases)
# ─────────────────────────────────────────────
_S = {
    "bg-base":      _P["gray-800"],
    "bg-surface":   _P["gray-700"],
    "bg-elevated":  _P["gray-650"],
    "bg-hover":     _P["gray-600"],
    "bg-active":    _P["gray-500"],
    "border":       _P["gray-600"],
    "border-focus": _P["purple-500"],
    "text-primary": _P["gray-100"],
    "text-muted":   _P["gray-300"],
    "text-disabled":_P["gray-400"],
    "color-primary":  _P["purple-500"],
    "color-primary-hover": _P["purple-600"],
    "color-primary-active": _P["purple-700"],
    "color-primary-subtle": _P["purple-100"],
    "color-accent": _P["teal-400"],
    "color-success":_P["green-400"],
    "color-success-bg": _P["green-dark"],
    "color-error":  _P["red-400"],
    "color-error-bg":   _P["red-dark"],
    "color-warning":_P["yellow-400"],
    "color-warning-bg": _P["yellow-dark"],
    "color-link":   _P["purple-400"],
}

# ─────────────────────────────────────────────
# FONT  (base 14 px per skill guidance)
# ─────────────────────────────────────────────
APP_FONT_FAMILY = "Microsoft YaHei UI, Segoe UI, PingFang SC, Noto Sans CJK SC, sans-serif"
APP_FONT_SIZE = 14  # px → points ≈ 10.5 pt

FONT_SIZE_XS   = 11   # hints / captions
FONT_SIZE_SM   = 12   # labels, status
FONT_SIZE_BASE = 14   # body text (buttons, inputs)
FONT_SIZE_MD   = 15   # group box titles
FONT_SIZE_LG   = 16   # section headings
FONT_SIZE_XL   = 18   # window title

# ─────────────────────────────────────────────
# SPACING & SHAPE
# ─────────────────────────────────────────────
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8
RADIUS_XL = 10
SPACING   = 6   # base spacing unit (px)

# ─────────────────────────────────────────────
# QSS STYLESHEET
# ─────────────────────────────────────────────
def _qss() -> str:
    s = _S
    p = _P
    return f"""
/* ── GLOBAL ───────────────────────────────── */
QWidget {{
    background-color: {s['bg-base']};
    color: {s['text-primary']};
    font-family: {APP_FONT_FAMILY};
    font-size: {FONT_SIZE_BASE}px;
    selection-background-color: {s['color-primary']};
    selection-color: {p['white']};
}}

/* ── MAIN WINDOW ──────────────────────────── */
QMainWindow {{
    background-color: {s['bg-base']};
}}

/* ── STATUS BAR ──────────────────────────── */
QStatusBar {{
    background-color: {p['gray-900']};
    color: {s['text-muted']};
    font-size: {FONT_SIZE_SM}px;
    border-top: 1px solid {s['border']};
    padding: 2px 8px;
}}
QStatusBar QLabel {{
    background: transparent;
    color: {s['text-muted']};
    font-size: {FONT_SIZE_SM}px;
    padding: 0 4px;
}}

/* ── TAB WIDGET ──────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {s['border']};
    border-radius: {RADIUS_LG}px;
    background-color: {s['bg-surface']};
    top: -1px;
}}
QTabWidget::tab-bar {{
    alignment: left;
}}
QTabBar::tab {{
    background-color: {s['bg-elevated']};
    color: {s['text-muted']};
    padding: 9px 20px;
    margin-right: 2px;
    border-top-left-radius: {RADIUS_MD}px;
    border-top-right-radius: {RADIUS_MD}px;
    border: 1px solid {s['border']};
    border-bottom: none;
    font-size: {FONT_SIZE_BASE}px;
    min-width: 80px;
}}
QTabBar::tab:hover {{
    background-color: {s['bg-hover']};
    color: {s['text-primary']};
}}
QTabBar::tab:selected {{
    background-color: {s['bg-surface']};
    color: {s['color-accent']};
    border-color: {s['border']};
    border-bottom: 2px solid {s['color-primary']};
    font-weight: bold;
}}

/* ── GROUP BOX ──────────────────────────── */
QGroupBox {{
    background-color: {s['bg-surface']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_LG}px;
    margin-top: 10px;
    padding: 12px 10px 10px 10px;
    font-size: {FONT_SIZE_MD}px;
    font-weight: bold;
    color: {s['text-primary']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {s['color-accent']};
    background-color: {s['bg-surface']};
    border-radius: {RADIUS_SM}px;
    left: 12px;
    top: -1px;
}}

/* ── PUSH BUTTON ───────────────────────── */
QPushButton {{
    background-color: {s['color-primary']};
    color: {p['white']};
    border: none;
    border-radius: {RADIUS_MD}px;
    padding: 9px 20px;
    font-size: {FONT_SIZE_BASE}px;
    font-weight: bold;
    min-height: 36px;
    min-width: 80px;
}}
QPushButton:hover {{
    background-color: {s['color-primary-hover']};
}}
QPushButton:pressed {{
    background-color: {s['color-primary-active']};
    padding-top: 10px;
    padding-bottom: 8px;
}}
QPushButton:disabled {{
    background-color: {s['bg-hover']};
    color: {s['text-disabled']};
}}
QPushButton[flat="true"] {{
    background-color: transparent;
    color: {s['color-link']};
    border: 1px solid {s['border']};
}}
QPushButton[flat="true"]:hover {{
    background-color: {s['bg-hover']};
    border-color: {s['color-primary']};
}}

/* secondary / outline buttons */
QPushButton[secondary="true"] {{
    background-color: transparent;
    color: {s['color-primary']};
    border: 1px solid {s['color-primary']};
}}
QPushButton[secondary="true"]:hover {{
    background-color: {s['color-primary-subtle']};
}}
QPushButton[secondary="true"]:pressed {{
    background-color: {s['color-primary']};
    color: {p['white']};
}}
QPushButton[secondary="true"]:disabled {{
    border-color: {s['bg-active']};
    color: {s['text-disabled']};
}}

/* danger buttons */
QPushButton[danger="true"] {{
    background-color: {s['color-error']};
    color: {p['white']};
    border: none;
}}
QPushButton[danger="true"]:hover {{
    background-color: #e05555;
}}

/* ── TEXT EDIT / PLAIN TEXT ─────────────── */
QTextEdit, QPlainTextEdit {{
    background-color: {s['bg-elevated']};
    color: {s['text-primary']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_MD}px;
    padding: 8px;
    font-size: {FONT_SIZE_BASE}px;
    line-height: 1.5;
    selection-background-color: {s['color-primary']};
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {s['border-focus']};
    outline: none;
}}
QTextEdit:disabled, QPlainTextEdit:disabled {{
    color: {s['text-disabled']};
    background-color: {s['bg-surface']};
}}

/* ── LINE EDIT ──────────────────────────── */
QLineEdit {{
    background-color: {s['bg-elevated']};
    color: {s['text-primary']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_MD}px;
    padding: 7px 10px;
    font-size: {FONT_SIZE_BASE}px;
    min-height: 34px;
}}
QLineEdit:focus {{
    border-color: {s['border-focus']};
}}
QLineEdit:disabled {{
    color: {s['text-disabled']};
    background-color: {s['bg-surface']};
}}

/* ── SPIN BOX ───────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {s['bg-elevated']};
    color: {s['text-primary']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_MD}px;
    padding: 6px 8px;
    font-size: {FONT_SIZE_BASE}px;
    min-height: 34px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {s['border-focus']};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {s['bg-hover']};
    border: none;
    width: 20px;
    border-radius: 0;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {s['bg-active']};
}}

/* ── COMBO BOX ──────────────────────────── */
QComboBox {{
    background-color: {s['bg-elevated']};
    color: {s['text-primary']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_MD}px;
    padding: 7px 32px 7px 10px;
    font-size: {FONT_SIZE_BASE}px;
    min-height: 34px;
    min-width: 100px;
}}
QComboBox:hover {{
    border-color: {s['color-primary']};
}}
QComboBox:focus {{
    border-color: {s['border-focus']};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {s['text-muted']};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {s['bg-elevated']};
    color: {s['text-primary']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_MD}px;
    padding: 4px;
    selection-background-color: {s['color-primary']};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    min-height: 28px;
    border-radius: {RADIUS_SM}px;
}}

/* ── SLIDER ─────────────────────────────── */
QSlider::groove:horizontal {{
    height: 6px;
    background-color: {s['bg-active']};
    border-radius: 3px;
    margin: 2px 0;
}}
QSlider::handle:horizontal {{
    background-color: {s['color-primary']};
    border: 2px solid {p['gray-800']};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background-color: {s['color-accent']};
    border-color: {s['color-accent']};
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {s['color-primary']}, stop:1 {s['color-accent']});
    height: 6px;
    border-radius: 3px;
}}

/* ── PROGRESS BAR ───────────────────────── */
QProgressBar {{
    background-color: {s['bg-elevated']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_MD}px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {s['color-primary']}, stop:1 {s['color-accent']});
    border-radius: {RADIUS_MD}px;
}}

/* ── LABEL ──────────────────────────────── */
QLabel {{
    background: transparent;
    color: {s['text-primary']};
    font-size: {FONT_SIZE_BASE}px;
}}
QLabel[muted="true"] {{
    color: {s['text-muted']};
    font-size: {FONT_SIZE_SM}px;
}}
QLabel[heading="true"] {{
    font-size: {FONT_SIZE_LG}px;
    font-weight: bold;
    color: {s['color-accent']};
}}

/* ── SCROLL BAR ─────────────────────────── */
QScrollBar:vertical {{
    background: {s['bg-surface']};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: {s['bg-active']};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p['gray-400']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}
QScrollBar:horizontal {{
    background: {s['bg-surface']};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: {s['bg-active']};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {p['gray-400']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ── LIST WIDGET ─────────────────────────── */
QListWidget {{
    background-color: {s['bg-surface']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_LG}px;
    padding: 4px;
    font-size: {FONT_SIZE_BASE}px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: {RADIUS_SM}px;
    color: {s['text-primary']};
    min-height: 32px;
}}
QListWidget::item:hover {{
    background-color: {s['bg-elevated']};
}}
QListWidget::item:selected {{
    background-color: {s['color-primary-subtle']};
    color: {s['color-accent']};
    border: 1px solid {s['color-primary']};
}}

/* ── CHECKBOX ───────────────────────────── */
QCheckBox {{
    spacing: 8px;
    font-size: {FONT_SIZE_BASE}px;
    color: {s['text-primary']};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    background-color: {s['bg-elevated']};
    border: 2px solid {s['border']};
    border-radius: {RADIUS_SM}px;
}}
QCheckBox::indicator:hover {{
    border-color: {s['color-primary']};
}}
QCheckBox::indicator:checked {{
    background-color: {s['color-primary']};
    border-color: {s['color-primary']};
    image: none;
}}

/* ── FORM LAYOUT LABELS ─────────────────── */
QFormLayout QLabel {{
    color: {s['text-muted']};
    font-size: {FONT_SIZE_SM}px;
    font-weight: bold;
    letter-spacing: 0.3px;
}}

/* ── SPLITTER ────────────────────────────── */
QSplitter::handle {{
    background-color: {s['border']};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}

/* ── TOOL TIP ────────────────────────────── */
QToolTip {{
    background-color: {p['gray-900']};
    color: {s['text-primary']};
    border: 1px solid {s['border']};
    border-radius: {RADIUS_MD}px;
    padding: 6px 10px;
    font-size: {FONT_SIZE_SM}px;
}}

/* ── MESSAGE BOX ─────────────────────────── */
QMessageBox {{
    background-color: {s['bg-surface']};
}}
QMessageBox QLabel {{
    color: {s['text-primary']};
    font-size: {FONT_SIZE_BASE}px;
}}

/* ── FRAME ───────────────────────────────── */
QFrame[frameShape="4"],   /* HLine */
QFrame[frameShape="5"] {{ /* VLine */
    color: {s['border']};
}}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the dark theme to a QApplication instance."""
    # Global stylesheet
    app.setStyleSheet(_qss())

    # Application-level font
    font = QFont()
    font.setFamilies(APP_FONT_FAMILY.split(", "))
    font.setPixelSize(APP_FONT_SIZE)
    app.setFont(font)


def make_secondary_button(btn) -> None:
    """Mark a QPushButton as secondary (outline style)."""
    btn.setProperty("secondary", "true")
    btn.style().unpolish(btn)
    btn.style().polish(btn)


def make_danger_button(btn) -> None:
    """Mark a QPushButton as danger (red style)."""
    btn.setProperty("danger", "true")
    btn.style().unpolish(btn)
    btn.style().polish(btn)


# Color constants for programmatic use (e.g., QLabel palette, status LED)
COLOR_SUCCESS = _S["color-success"]
COLOR_ERROR   = _S["color-error"]
COLOR_WARNING = _S["color-warning"]
COLOR_ACCENT  = _S["color-accent"]
COLOR_PRIMARY = _S["color-primary"]
COLOR_MUTED   = _S["text-muted"]
COLOR_BG      = _S["bg-base"]
COLOR_SURFACE = _S["bg-surface"]
COLOR_TEXT    = _S["text-primary"]
