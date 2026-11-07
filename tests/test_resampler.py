"""Unit tests for multi-scale downsampling pyramid and unsharp masking."""
import pytest
from PIL import Image
from src.core.resampler import IconResampler, ICON_SIZES


def test_generate_pyramid_sizes():
    master = Image.new("RGBA", (512, 512), color=(200, 100, 50, 255))
    resampler = IconResampler(sharpening_strength=1.0)
    pyramid = resampler.generate_pyramid(master)

    assert set(pyramid.keys()) == set(ICON_SIZES)
    for size, img in pyramid.items():
        assert img.size == (size, size)
        assert img.mode == "RGBA"


def test_sharpening_strength_zero_leaves_image_unchanged():
    master = Image.new("RGBA", (32, 32), color=(100, 150, 200, 255))
    resampler = IconResampler(sharpening_strength=0.0)
    sharpened = resampler.sharpen_image(master, 32)
    assert master.tobytes() == sharpened.tobytes()
