"""Integration tests for background segmentation and full pipeline."""
from pathlib import Path
import pytest
from PIL import Image
from src.core.aspect import FitMode
from src.core.pipeline import IconPipeline, PipelineOptions
from src.core.segmenter import BackgroundSegmenter


def test_segmenter_execution():
    segmenter = BackgroundSegmenter()
    if not segmenter.is_available:
        pytest.skip("u2netp.onnx model not downloaded or not available.")

    # Create dummy image: solid circle on solid white background
    img = Image.new("RGB", (300, 300), color=(255, 255, 255))
    result = segmenter.remove_background(img)

    assert result.mode == "RGBA"
    assert result.size == (300, 300)


def test_full_pipeline_with_export(tmp_path):
    pipeline = IconPipeline()

    # Create test input image
    input_file = tmp_path / "sample_logo.png"
    sample = Image.new("RGBA", (400, 200), color=(50, 150, 250, 255))
    sample.save(input_file)

    output_ico = tmp_path / "sample_logo.ico"
    options = PipelineOptions(
        fit_mode=FitMode.PAD,
        margin_ratio=0.1,
        remove_background=False,
        sharpening_strength=1.2,
        sizes=[16, 32, 48, 256]
    )

    result_path = pipeline.export(input_file, output_ico, options)
    assert result_path.exists()
    assert result_path.stat().st_size > 0

    # Verify PIL opens the generated ICO file
    with Image.open(result_path) as img:
        assert img.format == "ICO"
