"""Asynchronous worker thread for non-blocking icon processing."""
import traceback
from typing import Optional, Union
from pathlib import Path
from PIL import Image
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.core.pipeline import IconPipeline, PipelineOptions, PipelineResult


class WorkerSignals(QObject):
    """Signals emitted by the background icon processing worker."""
    started = pyqtSignal()
    finished = pyqtSignal(object)  # PipelineResult
    error = pyqtSignal(str)


class PipelineWorker(QThread):
    """
    Dedicated QThread worker executing neural segmentation and downsampling
    off the main GUI thread to prevent UI freezing.
    """

    def __init__(
        self,
        pipeline: IconPipeline,
        source: Union[str, Path, Image.Image],
        options: PipelineOptions,
        request_id: int = 0,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.pipeline = pipeline
        self.source = source
        self.options = options
        self.request_id = request_id
        self.signals = WorkerSignals()
        self._is_cancelled = False

    def cancel(self):
        """Mark this worker request as cancelled."""
        self._is_cancelled = True

    def run(self):
        if self._is_cancelled:
            return

        self.signals.started.emit()

        try:
            result = self.pipeline.process(self.source, self.options)
            if not self._is_cancelled:
                self.signals.finished.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                trace = traceback.format_exc()
                self.signals.error.emit(f"{str(e)}\n{trace}")
