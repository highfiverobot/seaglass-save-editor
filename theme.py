"""theme.py -- Gen-2 Pokedex light theme for the Seaglass editor.

A cream/beige Pokedex look built on two tones only: warm cream panels and the
Pokedex dark-red accent. The bundled Orange Kid pixel font is loaded at runtime
(works in source and the PyInstaller one-file build) and sized generously.
"""
import os
import sys

from PySide6.QtGui import QFontDatabase, QFont

# Cream + dark-red Pokedex palette.
PALETTE = dict(
    BG="#efe7cf",          # paper / cream background
    SURFACE="#f6efd9",     # panel cream
    SURFACE2="#fcf8ea",    # inputs / raised panels (lightest)
    BORDER="#8a2a20",      # dark-red frame
    BORDER_HI="#b5483a",   # lighter red highlight
    TEXT="#5a1f18",        # deep red-brown text
    TEXT_MUTED="#8a3a2e",  # muted red-brown
    ACCENT="#c0392b",      # Pokedex red
    ACCENT_HOVER="#d84b3b",
    ACCENT_PRESS="#8e2a20",
)


def _resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _load_font(app):
    """Register the bundled pixel font and set it as the application font."""
    path = _resource_path("orange-kid.regular.otf")
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
    f.setPixelSize(16)
    app.setFont(f)
    return family


def _build_qss(p, family):
    fam = f'"{family}"'
    return f"""
    * {{ font-family: {fam}, "MS Gothic", monospace; font-size: 16px; }}
    QMainWindow, QWidget#root {{ background: {p['BG']}; }}
    QWidget {{ color: {p['TEXT']}; }}
    QLabel {{ color: {p['TEXT']}; background: transparent; }}
    QLabel#header {{ color: {p['ACCENT']}; border: none; border-bottom: 3px solid {p['ACCENT']};
        padding: 2px 0 8px 0; font-size: 22px; font-weight: 700; }}
    QLabel#logo {{ background: transparent; }}
    QLabel#sprite {{ background: {p['SURFACE2']}; border: 3px solid {p['ACCENT']};
        border-radius: 6px; }}
    QLabel#info {{ background: {p['SURFACE2']}; color: {p['TEXT']};
        border: 2px solid {p['BORDER']}; border-radius: 4px; padding: 8px 10px; font-size: 15px; }}
    QCheckBox {{ color: {p['TEXT']}; font-weight: 700; spacing: 8px; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid {p['ACCENT']};
        border-radius: 3px; background: {p['SURFACE2']}; }}
    QCheckBox::indicator:checked {{ background: {p['ACCENT']}; border: 2px solid {p['ACCENT_PRESS']}; }}
    QGroupBox {{ background: {p['SURFACE']}; border: 2px solid {p['ACCENT']}; border-radius: 6px;
        margin-top: 18px; padding: 20px 12px 12px 12px; font-weight: 700; color: {p['ACCENT']}; }}
    QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 12px;
        padding: 0 6px; background: {p['SURFACE']}; color: {p['ACCENT']}; font-size: 15px; font-weight: 700; }}
    QPushButton {{ background: {p['SURFACE2']}; border: 2px solid {p['ACCENT']};
        border-radius: 5px; padding: 6px 12px; color: {p['ACCENT']}; font-weight: 700; }}
    QPushButton:hover {{ background: {p['SURFACE']}; border: 2px solid {p['ACCENT_PRESS']}; color: {p['ACCENT_PRESS']}; }}
    QPushButton:pressed {{ background: {p['ACCENT']}; color: #fff3e0; }}
    QPushButton:disabled {{ color: {p['TEXT_MUTED']}; background: {p['SURFACE']}; border: 2px solid {p['BORDER_HI']}; }}
    QPushButton#primary {{ background: {p['ACCENT']}; color: #fff3e0; border: 2px solid {p['ACCENT_PRESS']}; font-weight: 700; }}
    QPushButton#primary:hover {{ background: {p['ACCENT_HOVER']}; border: 2px solid {p['ACCENT_PRESS']}; }}
    QPushButton#primary:pressed {{ background: {p['ACCENT_PRESS']}; }}
    QComboBox, QLineEdit, QSpinBox {{ background: {p['SURFACE2']}; border: 2px solid {p['BORDER']};
        border-radius: 4px; padding: 4px 8px; min-height: 22px; color: {p['TEXT']};
        selection-background-color: {p['ACCENT']}; selection-color: #fff3e0; }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled {{ color: {p['TEXT_MUTED']};
        background: {p['SURFACE']}; border: 2px solid {p['BORDER_HI']}; }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border: 2px solid {p['ACCENT']}; }}
    QComboBox::drop-down {{ border: 0; width: 22px; }}
    QComboBox QAbstractItemView {{ background: {p['SURFACE2']}; border: 2px solid {p['BORDER']};
        selection-background-color: {p['ACCENT']}; selection-color: #fff3e0; outline: 0; padding: 4px; }}
    QToolButton {{ color: {p['ACCENT']}; background: {p['SURFACE2']};
        border: 2px solid {p['ACCENT']}; border-radius: 6px; padding: 6px 8px; font-weight: 700; }}
    QToolButton:hover {{ background: {p['SURFACE']}; }}
    QListWidget {{ background: {p['SURFACE']}; border: 2px solid {p['ACCENT']}; border-radius: 6px;
        padding: 6px; color: {p['TEXT']}; outline: 0; }}
    QListWidget::item {{ padding: 8px; border-radius: 4px; margin: 1px; }}
    QListWidget::item:selected {{ background: {p['ACCENT']}; color: #fff3e0; }}
    QListWidget::item:hover:!selected {{ background: {p['SURFACE2']}; }}
    QStatusBar {{ background: {p['SURFACE']}; color: {p['TEXT_MUTED']}; border-top: 2px solid {p['ACCENT']}; }}
    QStatusBar::item {{ border: 0; }}
    QScrollArea {{ background: transparent; border: 0; }}
    QScrollArea#logoScroll, QScrollArea#leftScroll {{ background: {p['SURFACE']}; border: 0; }}
    QScrollArea#logoScroll > QWidget > QWidget, QScrollArea#leftScroll > QWidget > QWidget {{ background: {p['SURFACE']}; }}
    QScrollArea#editorScroll {{ background: transparent; border: 0; }}
    QScrollArea#editorScroll > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: {p['SURFACE']}; width: 12px; margin: 2px; border-radius: 6px; }}
    QScrollBar::handle:vertical {{ background: {p['ACCENT']}; border-radius: 5px; min-height: 24px; }}
    QScrollBar::handle:vertical:hover {{ background: {p['ACCENT_PRESS']}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QSplitter::handle {{ background: {p['ACCENT']}; }}
    QSplitter::handle:horizontal {{ width: 3px; }}
    """


def apply_theme(app, window, palette=None):
    app.setStyle("Fusion")
    family = _load_font(app)
    app.setStyleSheet(_build_qss(PALETTE, family))