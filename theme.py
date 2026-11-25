"""theme.py -- Gen-2 Pokedex light theme for the Seaglass editor.

A cream/beige Pokedex look with a dark-red frame, olive text and the bundled
Pokemon Gb pixel font. Light background throughout. The pixel font is loaded at
runtime from the bundled .ttf (works in source and the PyInstaller one-file
build).
"""
import os
import sys

from PySide6.QtGui import QFontDatabase, QFont

# Gen-2 Pokedex light palette.
PALETTE = dict(
    BG="#e8e0c8",          # cream / paper background
    SURFACE="#f4eedb",     # lighter panel
    SURFACE2="#fbf7e9",    # inputs / raised panels
    BORDER="#8a7b52",      # olive-brown frame
    BORDER_HI="#b8a878",   # lighter frame highlight
    TEXT="#3a3423",        # dark olive text
    TEXT_MUTED="#6f6446",  # muted olive
    ACCENT="#c0392b",      # Pokedex red
    ACCENT_HOVER="#d84b3b",
    ACCENT_PRESS="#8e2a20",
)


def _resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _load_font(app):
    """Register the bundled pixel font and set it as the application font.
    Returns the family name to use in the stylesheet (falls back to a system
    font family if loading fails)."""
    path = _resource_path("PokemonGb-RAeo.ttf")
    family = None
    if os.path.exists(path):
        fid = QFontDatabase.addApplicationFont(path)
        if fid != -1:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family = fams[0]
    if not family:
        family = "Segoe UI"
    f = QFont(family)
    f.setPixelSize(15)
    app.setFont(f)
    return family


def _build_qss(p, family):
    fam = f'"{family}"'
    return f"""
    * {{ font-family: {fam}, "MS Gothic", monospace; font-size: 14px; }}
    QMainWindow, QWidget#root {{ background: {p['BG']}; }}
    QLabel {{ color: {p['TEXT']}; background: transparent; }}
    QLabel#header {{ color: {p['ACCENT']}; border: none; border-bottom: 3px solid {p['ACCENT']};
        padding: 4px 0 10px 0; font-size: 18px; font-weight: 700; letter-spacing: 1px; }}
    QLabel#logo {{ background: transparent; }}
    QLabel#sprite {{ background: {p['SURFACE2']}; border: 2px solid {p['BORDER']};
        border-radius: 6px; }}
    QLabel#info {{ background: {p['SURFACE2']}; color: {p['TEXT']};
        border: 2px solid {p['BORDER']}; border-radius: 4px; padding: 8px 10px; font-size: 13px; }}
    QCheckBox {{ color: {p['TEXT']}; font-weight: 600; spacing: 8px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border: 2px solid {p['BORDER']};
        border-radius: 3px; background: {p['SURFACE2']}; }}
    QCheckBox::indicator:checked {{ background: {p['ACCENT']}; border: 2px solid {p['ACCENT']}; }}
    QGroupBox {{ background: {p['SURFACE']}; border: 2px solid {p['BORDER']}; border-radius: 6px;
        margin-top: 16px; padding: 18px 12px 12px 12px; font-weight: 700; color: {p['ACCENT']}; }}
    QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 12px;
        padding: 0 6px; background: {p['SURFACE']}; color: {p['ACCENT']}; font-size: 12px; font-weight: 700; }}
    QPushButton {{ background: {p['SURFACE2']}; border: 2px solid {p['BORDER']};
        border-radius: 5px; padding: 6px 12px; color: {p['TEXT']}; font-weight: 600; }}
    QPushButton:hover {{ border: 2px solid {p['ACCENT']}; color: {p['ACCENT']}; }}
    QPushButton:pressed {{ background: {p['SURFACE']}; }}
    QPushButton:disabled {{ color: {p['TEXT_MUTED']}; background: {p['SURFACE']}; border: 2px solid {p['BORDER_HI']}; }}
    QPushButton#primary {{ background: {p['ACCENT']}; color: #fff7e6; border: 2px solid {p['ACCENT_PRESS']}; font-weight: 700; }}
    QPushButton#primary:hover {{ background: {p['ACCENT_HOVER']}; border: 2px solid {p['ACCENT_PRESS']}; }}
    QPushButton#primary:pressed {{ background: {p['ACCENT_PRESS']}; }}
    QComboBox, QLineEdit, QSpinBox {{ background: {p['SURFACE2']}; border: 2px solid {p['BORDER']};
        border-radius: 4px; padding: 4px 8px; min-height: 20px; color: {p['TEXT']};
        selection-background-color: {p['ACCENT']}; selection-color: #fff7e6; }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled {{ color: {p['TEXT_MUTED']};
        background: {p['SURFACE']}; border: 2px solid {p['BORDER_HI']}; }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border: 2px solid {p['ACCENT']}; }}
    QComboBox::drop-down {{ border: 0; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {p['SURFACE2']}; border: 2px solid {p['BORDER']};
        selection-background-color: {p['ACCENT']}; selection-color: #fff7e6; outline: 0; padding: 4px; }}
    QToolButton {{ color: {p['TEXT']}; }}
    QListWidget {{ background: {p['SURFACE']}; border: 2px solid {p['BORDER']}; border-radius: 6px;
        padding: 6px; color: {p['TEXT']}; outline: 0; }}
    QListWidget::item {{ padding: 8px; border-radius: 4px; margin: 1px; }}
    QListWidget::item:selected {{ background: {p['ACCENT']}; color: #fff7e6; }}
    QListWidget::item:hover:!selected {{ background: {p['SURFACE2']}; }}
    QStatusBar {{ background: {p['SURFACE']}; color: {p['TEXT_MUTED']}; border-top: 2px solid {p['BORDER']}; }}
    QStatusBar::item {{ border: 0; }}
    QScrollArea {{ background: transparent; border: 0; }}
    QScrollArea#editorScroll {{ background: transparent; border: 0; }}
    QScrollArea#editorScroll > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: {p['SURFACE']}; width: 12px; margin: 2px; border-radius: 6px; }}
    QScrollBar::handle:vertical {{ background: {p['BORDER']}; border-radius: 5px; min-height: 24px; }}
    QScrollBar::handle:vertical:hover {{ background: {p['ACCENT']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QSplitter::handle {{ background: {p['BORDER']}; }}
    """


def apply_theme(app, window, palette=None):
    app.setStyle("Fusion")
    family = _load_font(app)
    app.setStyleSheet(_build_qss(PALETTE, family))