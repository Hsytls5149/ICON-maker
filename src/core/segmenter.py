"""On-device AI background removal module powered by pure ONNX Runtime CPU."""
import os
import sys
from pathlib import Path
from typing import Optional, Union
import numpy as np
import onnxruntime as ort
from PIL import Image


def get_default_model_path() -> Path:
    """Resolve model location supporting source development, PyInstaller onefile and onedir bundles."""
    if hasattr(sys, "_MEIPASS"):
        meipass_model = Path(sys._MEIPASS) / "models" / "u2netp.onnx"
        if meipass_model.exists():
            return meipass_model

    # Check relative to current executable for PyInstaller onedir
    exe_dir = Path(sys.executable).resolve().parent
    for candidate in [
        exe_dir / "_internal" / "models" / "u2netp.onnx",
        exe_dir / "models" / "u2netp.onnx",
    ]:
        if candidate.is_file():
            return candidate

    return Path(__file__).resolve().parent.parent.parent / "models" / "u2netp.onnx"


DEFAULT_MODEL_PATH = get_default_model_path()


class BackgroundSegmenter:
    """
    High-performance on-device background segmentation using u2netp ONNX model.
    Runs entirely offline on CPU with zero PyTorch dependencies.
    """

    def __init__(self, model_path: Optional[Union[str, Path]] = None):
        if model_path is None:
            self.model_path = DEFAULT_MODEL_PATH
        else:
            self.model_path = Path(model_path)
            
        self._session: Optional[ort.InferenceSession] = None
        self._input_name: Optional[str] = None
        self._output_name: Optional[str] = None

    @property
    def is_available(self) -> bool:
        """Check whether the model file exists on disk."""
        return self.model_path.is_file()

    def _ensure_session(self) -> None:
        """Lazy initialization and caching of the ONNX InferenceSession."""
        if self._session is not None:
            return

        if not self.is_available:
            raise FileNotFoundError(
                f"Background removal model not found at '{self.model_path}'. "
                "Please ensure 'models/u2netp.onnx' is present."
            )

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = max(1, os.cpu_count() or 4)

        self._session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name
        self._output_name = self._session.get_outputs()[0].name

    def remove_background(
        self,
        image: Image.Image,
        alpha_threshold: float = 0.05,
        smooth_edges: bool = True
    ) -> Image.Image:
        """
        Segment the primary subject and strip the background.
        
        Args:
            image: Input PIL Image (RGB or RGBA).
            alpha_threshold: Minimum confidence below which alpha is snapped to 0.
            smooth_edges: Whether to apply edge smoothing to eliminate haloing.
            
        Returns:
            RGBA PIL Image with background removed.
        """
        self._ensure_session()

        # Preserve original dimensions and alpha channel if present
        orig_w, orig_h = image.size
        has_alpha = image.mode == "RGBA"
        orig_rgba = image.convert("RGBA")
        orig_alpha = np.array(orig_rgba.split()[3], dtype=np.float32) / 255.0 if has_alpha else None

        # Preprocess for u2netp (320x320, float32, normalized)
        rgb_img = orig_rgba.convert("RGB")
        resized_img = rgb_img.resize((320, 320), Image.Resampling.BILINEAR)
        img_data = np.array(resized_img, dtype=np.float32) / 255.0

        # Standard ImageNet normalization: (x - mean) / std
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (img_data - mean) / std

        # Shape: (1, 3, 320, 320)
        input_tensor = np.transpose(normalized, (2, 0, 1))[np.newaxis, :, :, :]

        # Inference
        outputs = self._session.run([self._output_name], {self._input_name: input_tensor})
        mask_raw = outputs[0][0, 0, :, :]  # (320, 320)

        # Min-max normalization of predicted saliency map to [0.0, 1.0]
        mask_min = float(mask_raw.min())
        mask_max = float(mask_raw.max())
        if mask_max - mask_min > 1e-6:
            mask_norm = (mask_raw - mask_min) / (mask_max - mask_min)
        else:
            mask_norm = np.zeros_like(mask_raw)

        # Resize mask back to original image size
        mask_img = Image.fromarray((mask_norm * 255.0).astype(np.uint8), mode="L")
        mask_resized = mask_img.resize((orig_w, orig_h), Image.Resampling.BILINEAR)
        pred_alpha = np.array(mask_resized, dtype=np.float32) / 255.0

        # Alpha thresholding & smoothing curve to eliminate fringing
        if smooth_edges:
            # Smoothstep sigmoid-like curve: 3x^2 - 2x^3
            t_low = alpha_threshold
            t_high = min(0.95, alpha_threshold + 0.5)
            clamped = np.clip((pred_alpha - t_low) / max(1e-5, (t_high - t_low)), 0.0, 1.0)
            pred_alpha = clamped * clamped * (3.0 - 2.0 * clamped)
        else:
            pred_alpha[pred_alpha < alpha_threshold] = 0.0

        # If original image already had transparency, multiply alpha channels
        if orig_alpha is not None:
            final_alpha = pred_alpha * orig_alpha
        else:
            final_alpha = pred_alpha

        # De-fringe RGB channels to prevent dark edge halos on light backgrounds
        final_alpha_uint8 = (final_alpha * 255.0).astype(np.uint8)
        alpha_channel = Image.fromarray(final_alpha_uint8, mode="L")

        r, g, b, _ = orig_rgba.split()
        result = Image.merge("RGBA", (r, g, b, alpha_channel))
        return result
