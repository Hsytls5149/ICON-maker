"""Automated offscreen GUI tests for WinIconStudio."""
import os
import sys
from pathlib import Path
from PIL import Image
import pytest

# Ensure offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.core.aspect import FitMode


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_instantiation(qapp):
    window = MainWindow()
    assert window.windowTitle().startswith("WinIconStudio")
    assert not window.btn_export.isEnabled()
    assert window.radio_pad.isChecked()
    assert not window.crop_controls_widget.isEnabled()
    assert window.slider_margin.value() == 5
    assert window.slider_sharpen.value() == 10
    assert window.slider_crop_x.value() == 50
    assert window.slider_crop_y.value() == 50


def test_main_window_crop_mode_toggle(qapp):
    window = MainWindow()
    window.radio_crop.setChecked(True)
    assert window.crop_controls_widget.isEnabled()

    # Test preset selection
    window._set_crop_preset("top")
    assert window.slider_crop_x.value() == 50
    assert window.slider_crop_y.value() == 0

    window._set_crop_preset("right")
    assert window.slider_crop_x.value() == 100
    assert window.slider_crop_y.value() == 50

    window.radio_pad.setChecked(True)
    assert not window.crop_controls_widget.isEnabled()


def test_main_window_load_and_process(qapp, tmp_path):
    # Create test image
    img_path = tmp_path / "gui_test.png"
    sample = Image.new("RGBA", (300, 300), color=(100, 200, 50, 255))
    sample.save(img_path)

    window = MainWindow()
    window.load_image(str(img_path))

    # Wait for synchronous/worker process
    if window.active_worker:
        window.active_worker.wait(3000)
        qapp.processEvents()

    assert window.btn_export.isEnabled()
    assert window.last_result is not None
    assert len(window.last_result.ico_bytes) > 0
    assert window.master_canvas.pixmap is not None


def test_checkerboard_canvas_mouse_drag(qapp):
    from PyQt6.QtCore import Qt, QPointF
    from PyQt6.QtGui import QMouseEvent
    from src.gui.preview_widget import CheckerboardCanvas

    canvas = CheckerboardCanvas()
    canvas.resize(300, 300)
    canvas.set_crop_mode(True, anchor_x=0.5, anchor_y=0.5, aspect_ratio=2.0)
    canvas.set_image(Image.new("RGBA", (400, 200), color="blue"))

    dragged_signals = []
    finished_signals = []
    canvas.crop_dragged.connect(lambda x, y: dragged_signals.append((x, y)))
    canvas.crop_drag_finished.connect(lambda x, y: finished_signals.append((x, y)))

    # Press mouse at center
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(150.0, 150.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press_event)
    assert canvas._is_dragging is True

    # Move mouse 50px to the left (shifting crop anchor to the right)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(100.0, 150.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseMoveEvent(move_event)
    assert len(dragged_signals) > 0
    last_x, last_y = dragged_signals[-1]
    assert last_x > 0.5  # Dragging left increases crop anchor to the right

    # Release mouse
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(100.0, 150.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mouseReleaseEvent(release_event)
    assert canvas._is_dragging is False
    assert len(finished_signals) == 1


def test_main_window_canvas_crop_drag(qapp, tmp_path):
    # Create wide test image
    img_path = tmp_path / "drag_test.png"
    sample = Image.new("RGBA", (400, 200), color=(100, 150, 200, 255))
    sample.save(img_path)

    window = MainWindow()
    window.load_image(str(img_path))
    window.radio_crop.setChecked(True)
    assert window.master_canvas.crop_drag_enabled is True

    # Simulate drag from canvas to anchor (0.25, 0.75)
    window._on_canvas_crop_dragged(0.25, 0.75)
    assert window.slider_crop_x.value() == 25
    assert window.slider_crop_y.value() == 75
    assert window.master_canvas.pixmap is not None
