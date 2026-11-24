"""theme.py -- flat, minimal card/input aesthetic for the Seaglass editor.
Only the color tokens change per theme. Ported/trimmed from the MIT reference.
"""

PALETTES = {
    "teal": dict(
        BG="#0b0b0d", SURFACE="#151517", SURFACE2="#1d1d20", BORDER="#26262a",
        BORDER_HI="#38383e", TEXT="#f2f2f3", TEXT_MUTED="#8f8f97", ACCENT="#14b8a6",
        ACCENT_HOVER="#2dd4bf", ACCENT_PRESS="#0f766e",
    ),
    "emerald": dict(
        BG="#0a1810", SURFACE="#122318", SURFACE2="#1a2f21", BORDER="#26402f",
        BORDER_HI="#3a5c44", TEXT="#e4f3ea", TEXT_MUTED="#8fae9c", ACCENT="#46c98a",
        ACCENT_HOVER="#5fd89b", ACCENT_PRESS="#1f7d4f",
    ),
}
DEFAULT_THEME = "teal"


def _build_qss(p):
    return f"""
    * {{ font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif; font-size: 13px; }}
    QMainWindow, QWidget#root {{ background: {p['BG']}; }}
    QLabel {{ color: {p['TEXT']}; background: transparent; }}
    QLabel#header {{ color: {p['TEXT']}; border: none; border-bottom: 1px solid {p['BORDER']};
        padding: 2px 0 14px 0; font-size: 15px; font-weight: 600; }}
    QLabel#sprite {{ background: {p['SURFACE']}; border: 1px solid {p['BORDER']}; border-radius: 8px; }}
    QLabel#info {{ background: {p['SURFACE']}; color: {p['TEXT_MUTED']}; border: 1px solid {p['BORDER']};
        border-radius: 6px; padding: 8px 10px; font-family: "Consolas","DejaVu Sans Mono",monospace; font-size: 12px; }}
    QCheckBox {{ color: {p['TEXT']}; font-weight: 500; spacing: 8px; }}
    QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {p['BORDER_HI']};
        border-radius: 4px; background: {p['SURFACE2']}; }}
    QCheckBox::indicator:checked {{ background: {p['ACCENT']}; border: 1px solid {p['ACCENT']}; }}
    QGroupBox {{ background: {p['SURFACE']}; border: 1px solid {p['BORDER']}; border-radius: 10px;
        margin-top: 14px; padding: 18px 14px 14px 14px; font-weight: 600; color: {p['TEXT_MUTED']}; }}
    QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 14px;
        padding: 0 6px; background: {p['SURFACE']}; color: {p['TEXT_MUTED']}; font-size: 11px; font-weight: 600; }}
    QPushButton {{ background: {p['SURFACE2']}; border: 1px solid {p['BORDER_HI']}; border-radius: 8px;
        padding: 7px 14px; color: {p['TEXT']}; font-weight: 500; }}
    QPushButton:hover {{ border: 1px solid {p['ACCENT']}; }}
    QPushButton:pressed {{ background: {p['BG']}; }}
    QPushButton:disabled {{ color: {p['TEXT_MUTED']}; background: {p['SURFACE']}; border: 1px solid {p['BORDER']}; }}
    QPushButton#primary {{ background: {p['ACCENT']}; color: #ffffff; border: 1px solid {p['ACCENT']}; font-weight: 600; }}
    QPushButton#primary:hover {{ background: {p['ACCENT_HOVER']}; border: 1px solid {p['ACCENT_HOVER']}; }}
    QPushButton#primary:pressed {{ background: {p['ACCENT_PRESS']}; }}
    QComboBox, QLineEdit, QSpinBox {{ background: {p['SURFACE2']}; border: 1px solid {p['BORDER_HI']};
        border-radius: 6px; padding: 5px 10px; min-height: 20px; color: {p['TEXT']};
        selection-background-color: {p['ACCENT']}; selection-color: #ffffff; }}
    QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled {{ color: {p['TEXT_MUTED']};
        background: {p['SURFACE']}; border: 1px solid {p['BORDER']}; }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border: 1px solid {p['ACCENT']}; }}
    QComboBox::drop-down {{ border: 0; width: 24px; }}
    QComboBox QAbstractItemView {{ background: {p['SURFACE2']}; border: 1px solid {p['BORDER_HI']};
        border-radius: 6px; selection-background-color: {p['ACCENT']}; selection-color: #ffffff; outline: 0; padding: 4px; }}
    QListWidget {{ background: {p['SURFACE']}; border: 1px solid {p['BORDER']}; border-radius: 10px;
        padding: 6px; color: {p['TEXT']}; outline: 0; }}
    QListWidget::item {{ padding: 8px; border-radius: 6px; margin: 1px; }}
    QListWidget::item:selected {{ background: {p['ACCENT']}; color: #ffffff; }}
    QListWidget::item:hover:!selected {{ background: {p['SURFACE2']}; }}
    QStatusBar {{ background: {p['BG']}; color: {p['TEXT_MUTED']}; border-top: 1px solid {p['BORDER']}; }}
    QStatusBar::item {{ border: 0; }}
    QScrollArea#editorScroll {{ background: transparent; border: 0; }}
    QScrollArea#editorScroll > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p['BORDER_HI']}; border-radius: 5px; min-height: 24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    """


def apply_theme(app, window, palette=DEFAULT_THEME):
    app.setStyle("Fusion")
    app.setStyleSheet(_build_qss(PALETTES[palette]))
