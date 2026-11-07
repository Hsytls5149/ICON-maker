"""Preview widgets and Explorer Simulation Matrix for WinIconStudio."""
import io
from typing import Dict, Optional
from PIL import Image
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QGridLayout,
)

from src.core.pipeline import SUPPORTED_EXTENSIONS


def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Convert a PIL Image (RGBA) into a QPixmap cleanly via memory buffer."""
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    
    # Save to in-memory PNG buffer for lossless QPixmap loading
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    buffer.seek(0)
    
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap


class CheckerboardCanvas(QFrame):
    """
    A canvas that paints a subtle transparency checkerboard pattern
    and supports interactive mouse dragging to adjust the crop position in real time.
    """

    crop_dragged = pyqtSignal(float, float)        # (anchor_x, anchor_y)
    crop_drag_finished = pyqtSignal(float, float) # (anchor_x, anchor_y)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(280, 280)
        self.pixmap: Optional[QPixmap] = None
        self.check_size = 12

        # Crop dragging state
        self.crop_drag_enabled: bool = False
        self.anchor_x: float = 0.5
        self.anchor_y: float = 0.5
        self.aspect_ratio: float = 1.0
        self.is_hovered: bool = False
        self._is_dragging: bool = False
        self._drag_start_pos = None
        self._drag_start_anchor_x = 0.5
        self._drag_start_anchor_y = 0.5

        self.setMouseTracking(True)

    def set_crop_mode(
        self,
        enabled: bool,
        anchor_x: float = 0.5,
        anchor_y: float = 0.5,
        aspect_ratio: float = 1.0
    ):
        """Configure whether interactive mouse dragging for crop adjustment is active."""
        self.crop_drag_enabled = enabled
        self.anchor_x = max(0.0, min(1.0, anchor_x))
        self.anchor_y = max(0.0, min(1.0, anchor_y))
        self.aspect_ratio = max(0.01, aspect_ratio)
        if enabled:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_anchor(self, anchor_x: float, anchor_y: float):
        """Update internal anchor positions."""
        self.anchor_x = max(0.0, min(1.0, anchor_x))
        self.anchor_y = max(0.0, min(1.0, anchor_y))
        self.update()

    def set_image(self, pil_img: Optional[Image.Image]):
        if pil_img is not None:
            self.pixmap = pil_to_qpixmap(pil_img)
        else:
            self.pixmap = None
        self.update()

    def enterEvent(self, event):
        self.is_hovered = True
        if self.crop_drag_enabled and not self._is_dragging:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()

    def leaveEvent(self, event):
        self.is_hovered = False
        if not self._is_dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def mousePressEvent(self, event):
        if self.crop_drag_enabled and event.button() == Qt.MouseButton.LeftButton and self.pixmap:
            self._is_dragging = True
            self._drag_start_pos = event.pos()
            self._drag_start_anchor_x = self.anchor_x
            self._drag_start_anchor_y = self.anchor_y
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._drag_start_pos:
            dx = event.pos().x() - self._drag_start_pos.x()
            dy = event.pos().y() - self._drag_start_pos.y()

            w = self.width()
            h = self.height()
            s_disp = max(80.0, float(min(w - 24, h - 24)))

            # Sensitivity tuned to 1:1 movement relative to excess image dimension
            if self.aspect_ratio > 1.001:  # Landscape
                excess_x = s_disp * (self.aspect_ratio - 1.0)
                sensitivity_x = max(40.0, excess_x)
                sensitivity_y = s_disp
            elif self.aspect_ratio < 0.999:  # Portrait
                excess_y = s_disp * ((1.0 / self.aspect_ratio) - 1.0)
                sensitivity_x = s_disp
                sensitivity_y = max(40.0, excess_y)
            else:  # Square
                sensitivity_x = s_disp
                sensitivity_y = s_disp

            # Dragging left moves the photo left (shifting crop anchor to the right)
            new_anchor_x = max(0.0, min(1.0, self._drag_start_anchor_x - (dx / sensitivity_x)))
            new_anchor_y = max(0.0, min(1.0, self._drag_start_anchor_y - (dy / sensitivity_y)))

            self.anchor_x = new_anchor_x
            self.anchor_y = new_anchor_y
            self.crop_dragged.emit(new_anchor_x, new_anchor_y)
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_dragging and event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            if self.crop_drag_enabled:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            self.crop_drag_finished.emit(self.anchor_x, self.anchor_y)
            self.update()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = self.width()
        h = self.height()

        # Draw checkerboard background
        color1 = QColor(245, 245, 248)
        color2 = QColor(230, 230, 235)
        for y in range(0, h, self.check_size):
            for x in range(0, w, self.check_size):
                if ((x // self.check_size) + (y // self.check_size)) % 2 == 0:
                    painter.fillRect(x, y, self.check_size, self.check_size, color1)
                else:
                    painter.fillRect(x, y, self.check_size, self.check_size, color2)

        # Draw centered pixmap if available
        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                QSize(w - 24, h - 24),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            px = (w - scaled.width()) // 2
            py = (h - scaled.height()) // 2
            painter.drawPixmap(px, py, scaled)

            # In crop mode, draw interactive drag border and hint badge
            if self.crop_drag_enabled:
                border_color = QColor(59, 130, 246, 200) if (self._is_dragging or self.is_hovered) else QColor(59, 130, 246, 90)
                painter.setPen(QPen(border_color, 2 if self._is_dragging else 1, Qt.PenStyle.DashLine if not self._is_dragging else Qt.PenStyle.SolidLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(px - 1, py - 1, scaled.width() + 2, scaled.height() + 2, 6, 6)

                # Draw floating pill hint
                badge_text = "✊ Dragging crop..." if self._is_dragging else "✋ Drag icon to reposition crop"
                font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
                painter.setFont(font)
                fm = painter.fontMetrics()
                text_w = fm.horizontalAdvance(badge_text)
                text_h = fm.height()

                badge_w = text_w + 20
                badge_h = text_h + 10
                bx = (w - badge_w) // 2
                by = h - badge_h - 12

                # Dark glass pill background
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(15, 23, 42, 210 if self._is_dragging else 170)))
                painter.drawRoundedRect(bx, by, badge_w, badge_h, badge_h // 2, badge_h // 2)

                # White text
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(bx, by, badge_w, badge_h, Qt.AlignmentFlag.AlignCenter, badge_text)

        # Canvas outline border
        painter.setPen(QPen(QColor(210, 210, 220), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, w - 1, h - 1)


class DropZoneWidget(QFrame):
    """Interactive drag-and-drop ingestion area with visual feedback."""

    file_dropped = pyqtSignal(str)
    clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_drag_over = False

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setContentsMargins(20, 20, 20, 20)

        self.icon_label = QLabel("📥", self)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 42px; margin-bottom: 8px;")

        self.title_label = QLabel("Drag & Drop Image Here", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #2D3748;")

        self.sub_label = QLabel("Supports PNG, JPG, JPEG, WEBP, BMP\nor click to browse", self)
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("font-size: 12px; color: #718096; margin-top: 4px;")

        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.sub_label)

        self._update_style()

    def _update_style(self):
        if self.is_drag_over:
            border = "2px dashed #3B82F6"
            bg = "#EFF6FF"
        else:
            border = "2px dashed #CBD5E1"
            bg = "#F8FAFC"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: {border};
                border-radius: 12px;
            }}
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                suffix = f".{url.fileName().split('.')[-1].lower()}"
                if suffix in SUPPORTED_EXTENSIONS:
                    self.is_drag_over = True
                    self._update_style()
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.is_drag_over = False
        self._update_style()

    def dropEvent(self, event):
        self.is_drag_over = False
        self._update_style()
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                suffix = f".{path.split('.')[-1].lower()}"
                if suffix in SUPPORTED_EXTENSIONS:
                    self.file_dropped.emit(path)
                    event.acceptProposedAction()
                    return

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class ExplorerSimulationMatrix(QWidget):
    """
    Displays the generated icon at 16px, 32px, 48px, and 256px
    across simulated Windows Dark (#1E1E1E) and Light (#F3F3F3) Explorer environments.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(16)

        title = QLabel("Explorer Simulation Matrix", self)
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #1E293B;")
        self.layout.addWidget(title)

        # Simulation Grid
        grid_widget = QWidget(self)
        self.grid = QGridLayout(grid_widget)
        self.grid.setSpacing(12)

        # Column Headers
        h_dark = QLabel("Dark Theme (Taskbar)", self)
        h_dark.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B;")
        h_light = QLabel("Light Theme (Explorer)", self)
        h_light.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B;")
        self.grid.addWidget(h_dark, 0, 1, Qt.AlignmentFlag.AlignCenter)
        self.grid.addWidget(h_light, 0, 2, Qt.AlignmentFlag.AlignCenter)

        # Rows for key sizes: 16px, 32px, 48px, 256px
        self.preview_sizes = [16, 32, 48, 256]
        self.size_labels: Dict[int, QLabel] = {}
        self.dark_tiles: Dict[int, QLabel] = {}
        self.light_tiles: Dict[int, QLabel] = {}

        for row_idx, size in enumerate(self.preview_sizes, start=1):
            lbl_desc = {
                16: "16px\n(Tray / List)",
                32: "32px\n(Details)",
                48: "48px\n(Desktop)",
                256: "256px\n(Jumbo)",
            }.get(size, f"{size}px")

            size_lbl = QLabel(lbl_desc, self)
            size_lbl.setStyleSheet("font-size: 11px; font-weight: 500; color: #475569;")
            size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.grid.addWidget(size_lbl, row_idx, 0)

            # Dark Tile
            dark_tile = QLabel(self)
            dark_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_h = max(size + 16, 44) if size < 128 else 140
            dark_tile.setFixedSize(QSize(140, tile_h))
            dark_tile.setStyleSheet("""
                QLabel {
                    background-color: #1E1E1E;
                    border: 1px solid #333333;
                    border-radius: 8px;
                }
            """)
            self.dark_tiles[size] = dark_tile
            self.grid.addWidget(dark_tile, row_idx, 1, Qt.AlignmentFlag.AlignCenter)

            # Light Tile
            light_tile = QLabel(self)
            light_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
            light_tile.setFixedSize(QSize(140, tile_h))
            light_tile.setStyleSheet("""
                QLabel {
                    background-color: #F8F9FA;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }
            """)
            self.light_tiles[size] = light_tile
            self.grid.addWidget(light_tile, row_idx, 2, Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(grid_widget)
        self.layout.addStretch()

    def update_previews(self, pyramid: Dict[int, Image.Image]):
        """Update all simulation tiles with newly generated pyramid images."""
        for size in self.preview_sizes:
            if size in pyramid:
                pil_img = pyramid[size]
                pixmap = pil_to_qpixmap(pil_img)

                # For 256px, fit it nicely inside the 140x140 tile
                if size == 256:
                    display_px = pixmap.scaled(
                        120, 120,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                else:
                    display_px = pixmap

                self.dark_tiles[size].setPixmap(display_px)
                self.light_tiles[size].setPixmap(display_px)
