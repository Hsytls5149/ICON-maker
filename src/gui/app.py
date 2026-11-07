"""Application entry point and Fluent Windows 11 styling."""
import sys
from pathlib import Path
from typing import Optional

# Ensure root package is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow

FLUENT_STYLESHEET = """
QMainWindow {
    background-color: #F8FAFC;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: #1E293B;
}

QGroupBox {
    font-size: 13px;
    font-weight: 600;
    color: #334155;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    background-color: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    background-color: #FFFFFF;
}

QRadioButton, QCheckBox {
    font-size: 12px;
    color: #334155;
    spacing: 8px;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
}

QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #E2E8F0;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #2563EB;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #2563EB;
    border: 2px solid #FFFFFF;
    width: 16px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #1D4ED8;
}

QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    color: #475569;
    font-size: 12px;
}
"""


def main(initial_image: Optional[str] = None):
    # Enable High-DPI attributes in Qt
    app = QApplication(sys.argv)
    app.setApplicationName("WinIconStudio")
    app.setOrganizationName("WinIconStudio")
    app.setStyleSheet(FLUENT_STYLESHEET)

    # Set default UI font to Segoe UI
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    image_arg = initial_image or (sys.argv[1] if len(sys.argv) > 1 else None)
    window = MainWindow(image_arg)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
