"""Deep-blue visual theme shared by the floating window chrome and the settings UI."""
from PyQt5.QtGui import QColor, QPalette

# palette
DEEP = "#12235E"          # deepest navy (window bg)
DEEP_2 = "#1B3A8F"        # panel / raised
BLUE = "#2E5BFF"          # accent
BLUE_SOFT = "#3F72FF"
GLASS = "#18307A"         # translucent-ish panels on stage
TEXT = "#EAF0FF"
TEXT_DIM = "#B9C6F2"
OK = "#57E39B"
ERR = "#FF7B7B"
WARN = "#FFC46B"

QSS = f"""
* {{
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
}}
QDialog {{
    background: {DEEP};
    color: {TEXT};
}}
QLabel {{
    color: {TEXT};
    background: transparent;
}}
QLabel[dim="true"] {{
    color: {TEXT_DIM};
}}
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background: #0C1A4D;
    border: 1px solid #27429F;
    border-radius: 7px;
    padding: 5px 8px;
    color: {TEXT};
    selection-background-color: {BLUE};
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {BLUE_SOFT};
}}
QComboBox {{
    background: #0C1A4D;
    border: 1px solid #27429F;
    border-radius: 7px;
    padding: 4px 8px;
    color: {TEXT};
}}
QComboBox QAbstractItemView {{
    background: #0C1A4D;
    color: {TEXT};
    selection-background-color: {BLUE};
    border: 1px solid #27429F;
}}
QPushButton {{
    background: {BLUE};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 7px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {BLUE_SOFT}; }}
QPushButton:pressed {{ background: #1E44C4; }}
QPushButton[flat="true"] {{
    background: transparent;
    border: 1px solid #4060D0;
    color: {TEXT};
}}
QPushButton[flat="true"]:hover {{ background: #1B2F78; }}
QCheckBox {{
    color: {TEXT};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid #4763CE;
    background: #0C1A4D;
}}
QCheckBox::indicator:checked {{
    background: {BLUE};
    border-color: {BLUE_SOFT};
}}
QRadioButton {{ color: {TEXT}; spacing: 6px; }}
QRadioButton::indicator {{
    width: 15px; height: 15px; border-radius: 8px;
    border: 1px solid #4763CE; background: #0C1A4D;
}}
QRadioButton::indicator:checked {{
    background: {BLUE};
    border: 3px solid #0C1A4D;
    border-radius: 8px;
}}
QSlider::groove:horizontal {{
    height: 5px; background: #27429F; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {BLUE}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 15px; height: 15px; margin: -6px 0;
    border-radius: 8px; background: #DDE7FF; border: 1px solid {BLUE_SOFT};
}}
QGroupBox {{
    border: 1px solid #27429F;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 6px;
    color: {TEXT_DIM};
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #27429F; border-radius: 5px; min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QToolTip {{
    background: #0C1A4D; color: {TEXT};
    border: 1px solid #27429F; padding: 4px;
}}
"""


def accent(hex_color: str) -> QColor:
    return QColor(hex_color)


def app_palette():
    p = QPalette()
    p.setColor(QPalette.Window, QColor(DEEP))
    p.setColor(QPalette.WindowText, QColor(TEXT))
    p.setColor(QPalette.Base, QColor("#0C1A4D"))
    p.setColor(QPalette.Text, QColor(TEXT))
    p.setColor(QPalette.Button, QColor(DEEP_2))
    p.setColor(QPalette.ButtonText, QColor(TEXT))
    p.setColor(QPalette.Highlight, QColor(BLUE))
    p.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    p.setColor(QPalette.ToolTipBase, QColor("#0C1A4D"))
    p.setColor(QPalette.ToolTipText, QColor(TEXT))
    return p
