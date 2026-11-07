"""Main Window for WinIconStudio Desktop Application."""
import sys
import time
from pathlib import Path
from typing import Optional, List
from PIL import Image

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QIcon, QFont, QColor
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QRadioButton,
    QSlider,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QGroupBox,
    QScrollArea,
    QSplitter,
    QButtonGroup,
)

from src.core.aspect import FitMode
from src.core.pipeline import IconPipeline, PipelineOptions, PipelineResult, SUPPORTED_EXTENSIONS
from src.core.resampler import ICON_SIZES
from src.gui.preview_widget import (
    CheckerboardCanvas,
    DropZoneWidget,
    ExplorerSimulationMatrix,
)
from src.gui.worker import PipelineWorker


class MainWindow(QMainWindow):
    """Primary application window with real-time controls and explorer simulation."""

    def __init__(self, initial_image_path: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("WinIconStudio — Custom Windows Folder & App Icon Generator")
        self.setMinimumSize(1080, 720)
        self.resize(1180, 780)

        self.pipeline = IconPipeline()
        self.current_image_path: Optional[str] = None
        self.current_raw_image: Optional[Image.Image] = None
        self.cached_segmented_image: Optional[Image.Image] = None
        self.cached_segmented_for_path: Optional[str] = None
        self.last_result: Optional[PipelineResult] = None
        self.active_worker: Optional[PipelineWorker] = None

        # Debounce timer for smooth slider interactions
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(100)
        self.debounce_timer.timeout.connect(self._execute_pipeline)

        self._init_ui()

        if initial_image_path and Path(initial_image_path).exists():
            self.load_image(initial_image_path)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Splitter between Sidebar and Preview Area
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(2)

        # 1. Controls Sidebar
        sidebar_widget = self._create_sidebar()
        splitter.addWidget(sidebar_widget)

        # 2. Preview Area
        preview_container = self._create_preview_container()
        splitter.addWidget(preview_container)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 780])

        main_layout.addWidget(splitter)

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready — drag and drop an image or click Browse to start", self)
        self.perf_label = QLabel("", self)
        self.perf_label.setStyleSheet("color: #64748B; font-weight: 500;")
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setVisible(False)

        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.perf_label)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _create_sidebar(self) -> QWidget:
        container = QWidget(self)
        container.setFixedWidth(360)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(14)

        # Header Title
        title_label = QLabel("Icon Configuration", container)
        title_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        layout.addWidget(title_label)

        # File Selection Group
        file_group = QGroupBox("Source Image", container)
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(8)

        self.btn_browse = QPushButton("📁 Browse Image File...", file_group)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: 600;
                color: #1E293B;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
                border-color: #94A3B8;
            }
        """)
        self.btn_browse.clicked.connect(self._on_browse_clicked)

        self.lbl_file_info = QLabel("No image loaded", file_group)
        self.lbl_file_info.setStyleSheet("color: #64748B; font-size: 11px;")
        self.lbl_file_info.setWordWrap(True)

        file_layout.addWidget(self.btn_browse)
        file_layout.addWidget(self.lbl_file_info)
        layout.addWidget(file_group)

        # AI Segmentation Group
        ai_group = QGroupBox("AI Background Removal", container)
        ai_layout = QVBoxLayout(ai_group)
        self.chk_remove_bg = QCheckBox("Remove background automatically (ONNX)", ai_group)
        self.chk_remove_bg.setStyleSheet("font-weight: 600; color: #1E293B;")
        self.chk_remove_bg.toggled.connect(self._schedule_reprocess)

        self.lbl_ai_status = QLabel(
            "Runs on-device via lightweight u2netp. No cloud upload required.", ai_group
        )
        self.lbl_ai_status.setStyleSheet("color: #64748B; font-size: 11px;")
        self.lbl_ai_status.setWordWrap(True)

        ai_layout.addWidget(self.chk_remove_bg)
        ai_layout.addWidget(self.lbl_ai_status)
        layout.addWidget(ai_group)

        # Aspect Ratio Fit Group
        aspect_group = QGroupBox("Aspect Ratio Fitting", container)
        aspect_layout = QVBoxLayout(aspect_group)

        self.radio_pad = QRadioButton("Pad with transparent canvas (Recommended)", aspect_group)
        self.radio_pad.setChecked(True)
        self.radio_pad.toggled.connect(self._on_fit_mode_changed)

        self.radio_crop = QRadioButton("Crop to square", aspect_group)
        self.radio_crop.toggled.connect(self._on_fit_mode_changed)

        self.fit_btn_group = QButtonGroup(aspect_group)
        self.fit_btn_group.addButton(self.radio_pad)
        self.fit_btn_group.addButton(self.radio_crop)

        aspect_layout.addWidget(self.radio_pad)
        aspect_layout.addWidget(self.radio_crop)

        # Configurable Crop Positioning Controls (active only when Cropping)
        self.crop_controls_widget = QWidget(aspect_group)
        crop_layout = QVBoxLayout(self.crop_controls_widget)
        crop_layout.setContentsMargins(12, 6, 0, 0)
        crop_layout.setSpacing(6)

        lbl_crop_anchor = QLabel("Crop Position / Alignment:", self.crop_controls_widget)
        lbl_crop_anchor.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        crop_layout.addWidget(lbl_crop_anchor)

        # Preset buttons row
        preset_bar = QHBoxLayout()
        preset_bar.setSpacing(4)
        for key, name in [("top", "Top"), ("left", "Left"), ("center", "Center"), ("right", "Right"), ("bottom", "Bottom")]:
            btn = QPushButton(name, self.crop_controls_widget)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F1F5F9;
                    border: 1px solid #CBD5E1;
                    border-radius: 4px;
                    padding: 3px 6px;
                    font-size: 11px;
                    font-weight: 600;
                    color: #334155;
                }
                QPushButton:hover {
                    background-color: #E2E8F0;
                    border-color: #94A3B8;
                }
            """)
            btn.clicked.connect(lambda checked, k=key: self._set_crop_preset(k))
            preset_bar.addWidget(btn)
        crop_layout.addLayout(preset_bar)

        # Horizontal Crop Slider (X)
        header_crop_x = QHBoxLayout()
        lbl_title_x = QLabel("Horizontal (X):", self.crop_controls_widget)
        lbl_title_x.setStyleSheet("font-size: 11px; color: #64748B;")
        self.lbl_crop_x_val = QLabel("50% (Center)", self.crop_controls_widget)
        self.lbl_crop_x_val.setStyleSheet("font-size: 11px; font-weight: 600; color: #2563EB;")
        header_crop_x.addWidget(lbl_title_x)
        header_crop_x.addStretch()
        header_crop_x.addWidget(self.lbl_crop_x_val)
        crop_layout.addLayout(header_crop_x)

        self.slider_crop_x = QSlider(Qt.Orientation.Horizontal, self.crop_controls_widget)
        self.slider_crop_x.setRange(0, 100)
        self.slider_crop_x.setValue(50)
        self.slider_crop_x.valueChanged.connect(self._on_crop_slider_changed)
        crop_layout.addWidget(self.slider_crop_x)

        # Vertical Crop Slider (Y)
        header_crop_y = QHBoxLayout()
        lbl_title_y = QLabel("Vertical (Y):", self.crop_controls_widget)
        lbl_title_y.setStyleSheet("font-size: 11px; color: #64748B;")
        self.lbl_crop_y_val = QLabel("50% (Center)", self.crop_controls_widget)
        self.lbl_crop_y_val.setStyleSheet("font-size: 11px; font-weight: 600; color: #2563EB;")
        header_crop_y.addWidget(lbl_title_y)
        header_crop_y.addStretch()
        header_crop_y.addWidget(self.lbl_crop_y_val)
        crop_layout.addLayout(header_crop_y)

        self.slider_crop_y = QSlider(Qt.Orientation.Horizontal, self.crop_controls_widget)
        self.slider_crop_y.setRange(0, 100)
        self.slider_crop_y.setValue(50)
        self.slider_crop_y.valueChanged.connect(self._on_crop_slider_changed)
        crop_layout.addWidget(self.slider_crop_y)

        self.crop_controls_widget.setEnabled(False)
        aspect_layout.addWidget(self.crop_controls_widget)
        layout.addWidget(aspect_group)

        # Inner Margin Slider
        margin_group = QGroupBox("Inner Margin / Breathing Room", container)
        margin_layout = QVBoxLayout(margin_group)

        margin_header = QHBoxLayout()
        lbl_margin_title = QLabel("Subject Margin:", margin_group)
        self.lbl_margin_val = QLabel("5%", margin_group)
        self.lbl_margin_val.setStyleSheet("font-weight: 700; color: #2563EB;")
        margin_header.addWidget(lbl_margin_title)
        margin_header.addStretch()
        margin_header.addWidget(self.lbl_margin_val)

        self.slider_margin = QSlider(Qt.Orientation.Horizontal, margin_group)
        self.slider_margin.setRange(0, 40)  # 0% to 40%
        self.slider_margin.setValue(5)
        self.slider_margin.valueChanged.connect(self._on_margin_changed)

        margin_layout.addLayout(margin_header)
        margin_layout.addWidget(self.slider_margin)
        layout.addWidget(margin_group)

        # Sharpening Multiplier Slider
        sharpen_group = QGroupBox("Micro-Scale Sharpening", container)
        sharpen_layout = QVBoxLayout(sharpen_group)

        sharpen_header = QHBoxLayout()
        lbl_sharpen_title = QLabel("Edge Sharpness:", sharpen_group)
        self.lbl_sharpen_val = QLabel("1.0x", sharpen_group)
        self.lbl_sharpen_val.setStyleSheet("font-weight: 700; color: #2563EB;")
        sharpen_header.addWidget(lbl_sharpen_title)
        sharpen_header.addStretch()
        sharpen_header.addWidget(self.lbl_sharpen_val)

        self.slider_sharpen = QSlider(Qt.Orientation.Horizontal, sharpen_group)
        self.slider_sharpen.setRange(0, 25)  # 0.0x to 2.5x (divided by 10)
        self.slider_sharpen.setValue(10)
        self.slider_sharpen.valueChanged.connect(self._on_sharpen_changed)

        sharpen_layout.addLayout(sharpen_header)
        sharpen_layout.addWidget(self.slider_sharpen)
        layout.addWidget(sharpen_group)

        # Resolution Checklist
        res_group = QGroupBox("Embedded Resolutions (.ICO)", container)
        res_layout = QGridLayout(res_group)
        self.res_checkboxes = {}
        for idx, size in enumerate(ICON_SIZES):
            chk = QCheckBox(f"{size} px", res_group)
            chk.setChecked(True)
            chk.toggled.connect(self._schedule_reprocess)
            self.res_checkboxes[size] = chk
            row = idx // 3
            col = idx % 3
            res_layout.addWidget(chk, row, col)
        layout.addWidget(res_group)

        layout.addStretch()

        # Primary Action: Export Button
        self.btn_export = QPushButton("🚀 Export .ICO File...", container)
        self.btn_export.setEnabled(False)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-size: 14px;
                font-weight: 700;
                padding: 12px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #94A3B8;
                color: #E2E8F0;
            }
        """)
        self.btn_export.clicked.connect(self._on_export_clicked)
        layout.addWidget(self.btn_export)

        return container

    def _create_preview_container(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(14)

        # Top section: Master Canvas and Drop Zone side-by-side or stacked
        top_split = QHBoxLayout()
        top_split.setSpacing(14)

        # Drop zone widget
        self.drop_zone = DropZoneWidget(container)
        self.drop_zone.file_dropped.connect(self.load_image)
        self.drop_zone.clicked.connect(self._on_browse_clicked)
        top_split.addWidget(self.drop_zone, 1)

        # Master Square Preview Canvas
        self.master_canvas = CheckerboardCanvas(container)
        self.master_canvas.setVisible(False)
        self.master_canvas.crop_dragged.connect(self._on_canvas_crop_dragged)
        self.master_canvas.crop_drag_finished.connect(self._on_canvas_crop_finished)
        top_split.addWidget(self.master_canvas, 1)

        layout.addLayout(top_split)

        # Bottom section: Explorer Simulation Matrix in a scroll area
        self.scroll_sim = QScrollArea(container)
        self.scroll_sim.setWidgetResizable(True)
        self.scroll_sim.setStyleSheet("QScrollArea { border: 1px solid #E2E8F0; border-radius: 8px; }")

        self.sim_matrix = ExplorerSimulationMatrix(self.scroll_sim)
        self.scroll_sim.setWidget(self.sim_matrix)
        layout.addWidget(self.scroll_sim, 2)

        return container

    def _on_browse_clicked(self):
        filters = "Supported Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", filters)
        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path: str):
        path = Path(file_path)
        if not path.is_file():
            QMessageBox.critical(self, "File Error", f"Cannot find image file:\n{file_path}")
            return

        try:
            self.current_raw_image = self.pipeline.load_image(path)
            self.current_image_path = str(path)
            self.cached_segmented_image = None
            self.cached_segmented_for_path = None

            w, h = self.current_raw_image.size
            self.lbl_file_info.setText(f"{path.name}\n{w} × {h} px ({self.current_raw_image.mode})")

            # Show master canvas and configure drop zone
            self.drop_zone.setVisible(False)
            self.master_canvas.setVisible(True)
            self.btn_export.setEnabled(True)

            # Update interactive canvas crop settings based on image aspect ratio
            aspect_ratio = w / max(1, h)
            self.master_canvas.set_crop_mode(
                enabled=self.radio_crop.isChecked(),
                anchor_x=self.slider_crop_x.value() / 100.0,
                anchor_y=self.slider_crop_y.value() / 100.0,
                aspect_ratio=aspect_ratio,
            )

            self._execute_pipeline()
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load image:\n{e}")

    def _on_fit_mode_changed(self):
        is_crop = self.radio_crop.isChecked()
        self.crop_controls_widget.setEnabled(is_crop)
        aspect_ratio = 1.0
        if self.current_raw_image:
            w, h = self.current_raw_image.size
            aspect_ratio = w / max(1, h)
        self.master_canvas.set_crop_mode(
            enabled=is_crop,
            anchor_x=self.slider_crop_x.value() / 100.0,
            anchor_y=self.slider_crop_y.value() / 100.0,
            aspect_ratio=aspect_ratio,
        )
        self._schedule_reprocess()

    def _set_crop_preset(self, preset_name: str):
        from src.core.aspect import CROP_ANCHOR_PRESETS
        coords = CROP_ANCHOR_PRESETS.get(preset_name, (0.5, 0.5))
        self.slider_crop_x.blockSignals(True)
        self.slider_crop_y.blockSignals(True)
        self.slider_crop_x.setValue(int(round(coords[0] * 100)))
        self.slider_crop_y.setValue(int(round(coords[1] * 100)))
        self.slider_crop_x.blockSignals(False)
        self.slider_crop_y.blockSignals(False)
        self._update_crop_labels()
        self.master_canvas.set_anchor(coords[0], coords[1])
        self._schedule_reprocess()

    def _on_crop_slider_changed(self):
        self._update_crop_labels()
        self.master_canvas.set_anchor(
            self.slider_crop_x.value() / 100.0,
            self.slider_crop_y.value() / 100.0
        )
        self._schedule_reprocess()

    def _on_canvas_crop_dragged(self, anchor_x: float, anchor_y: float):
        """Handle real-time mouse drag events on the master preview canvas."""
        if not self.current_raw_image or not self.radio_crop.isChecked():
            return

        # Synchronize sidebar sliders smoothly
        self.slider_crop_x.blockSignals(True)
        self.slider_crop_y.blockSignals(True)
        self.slider_crop_x.setValue(int(round(anchor_x * 100)))
        self.slider_crop_y.setValue(int(round(anchor_y * 100)))
        self.slider_crop_x.blockSignals(False)
        self.slider_crop_y.blockSignals(False)
        self._update_crop_labels()

        # Instantaneous 60fps fast master crop preview
        source_img = self.current_raw_image
        if self.chk_remove_bg.isChecked() and self.cached_segmented_image is not None and self.cached_segmented_for_path == self.current_image_path:
            source_img = self.cached_segmented_image

        from src.core.aspect import fit_to_square
        fast_master = fit_to_square(
            image=source_img,
            target_size=512,
            mode=FitMode.CROP,
            margin_ratio=self.slider_margin.value() / 100.0,
            crop_anchor=(anchor_x, anchor_y),
        )
        self.master_canvas.set_image(fast_master)

        # Reset debounce timer for simulation matrix and ICO container updates
        self.debounce_timer.start(120)

    def _on_canvas_crop_finished(self, anchor_x: float, anchor_y: float):
        """Finalize icon processing when mouse drag is released."""
        self._execute_pipeline()

    def _update_crop_labels(self):
        x_val = self.slider_crop_x.value()
        y_val = self.slider_crop_y.value()
        x_desc = "Left" if x_val == 0 else ("Right" if x_val == 100 else ("Center" if x_val == 50 else f"{x_val}%"))
        y_desc = "Top" if y_val == 0 else ("Bottom" if y_val == 100 else ("Center" if y_val == 50 else f"{y_val}%"))
        self.lbl_crop_x_val.setText(f"{x_val}% ({x_desc})" if x_desc != f"{x_val}%" else f"{x_val}%")
        self.lbl_crop_y_val.setText(f"{y_val}% ({y_desc})" if y_desc != f"{y_val}%" else f"{y_val}%")

    def _on_margin_changed(self, val: int):
        self.lbl_margin_val.setText(f"{val}%")
        self._schedule_reprocess()

    def _on_sharpen_changed(self, val: int):
        multiplier = val / 10.0
        self.lbl_sharpen_val.setText(f"{multiplier:.1f}x")
        self._schedule_reprocess()

    def _schedule_reprocess(self):
        if not self.current_raw_image:
            return
        self.debounce_timer.start()

    def _get_active_sizes(self) -> List[int]:
        sizes = [s for s, chk in self.res_checkboxes.items() if chk.isChecked()]
        return sorted(sizes) if sizes else [256]

    def _execute_pipeline(self):
        if not self.current_raw_image:
            return

        # Cancel any running background worker
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            self.active_worker.wait(100)

        remove_bg = self.chk_remove_bg.isChecked()
        fit_mode = FitMode.PAD if self.radio_pad.isChecked() else FitMode.CROP
        margin_ratio = self.slider_margin.value() / 100.0
        sharpening_strength = self.slider_sharpen.value() / 10.0
        sizes = self._get_active_sizes()

        crop_anchor = (
            self.slider_crop_x.value() / 100.0,
            self.slider_crop_y.value() / 100.0,
        )

        options = PipelineOptions(
            fit_mode=fit_mode,
            margin_ratio=margin_ratio,
            remove_background=remove_bg,
            sharpening_strength=sharpening_strength,
            sizes=sizes,
            crop_anchor=crop_anchor,
        )

        # Check if we can reuse the cached segmented image to save time
        source_image = self.current_raw_image
        if remove_bg and self.cached_segmented_image is not None and self.cached_segmented_for_path == self.current_image_path:
            source_image = self.cached_segmented_image
            options.remove_background = False  # Already segmented!

        self.progress_bar.setVisible(True)
        self.status_label.setText("Processing icon pipeline...")
        self.perf_t0 = time.perf_counter()

        self.active_worker = PipelineWorker(self.pipeline, source_image, options, parent=self)
        self.active_worker.signals.finished.connect(self._on_pipeline_success)
        self.active_worker.signals.error.connect(self._on_pipeline_error)
        self.active_worker.start()

    @pyqtSlot(object)
    def _on_pipeline_success(self, result: PipelineResult):
        self.progress_bar.setVisible(False)
        self.last_result = result
        elapsed_ms = (time.perf_counter() - self.perf_t0) * 1000

        # Cache segmentation if freshly performed
        if self.chk_remove_bg.isChecked() and result.segmented_image is not None:
            self.cached_segmented_image = result.segmented_image
            self.cached_segmented_for_path = self.current_image_path

        # Update Master Canvas and Explorer Simulation Matrix
        self.master_canvas.set_image(result.master_square)
        self.sim_matrix.update_previews(result.pyramid)

        self.status_label.setText("Ready")
        self.perf_label.setText(f"Pipeline latency: {elapsed_ms:.1f} ms | File size: {len(result.ico_bytes):,} B")

    @pyqtSlot(str)
    def _on_pipeline_error(self, err_msg: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error during processing")
        QMessageBox.warning(self, "Processing Warning", f"Could not process image:\n{err_msg}")

    def _on_export_clicked(self):
        if not self.last_result or not self.current_image_path:
            return

        default_name = Path(self.current_image_path).stem + ".ico"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Windows Icon",
            default_name,
            "Windows Icon (*.ico);;All Files (*.*)"
        )
        if save_path:
            try:
                Path(save_path).write_bytes(self.last_result.ico_bytes)
                self.status_label.setText(f"Exported successfully to {Path(save_path).name}")
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Successfully generated Windows icon:\n{save_path}\n\n"
                    f"File Size: {len(self.last_result.ico_bytes):,} bytes\n"
                    f"Embedded Resolutions: {len(self._get_active_sizes())}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save file:\n{e}")
