"""Unit tests for aspect ratio transformation and canvas fitting."""
import pytest
from PIL import Image
from src.core.aspect import fit_to_square, normalize_to_rgba, FitMode, parse_crop_anchor


def test_parse_crop_anchor():
    assert parse_crop_anchor("center") == (0.5, 0.5)
    assert parse_crop_anchor("top") == (0.5, 0.0)
    assert parse_crop_anchor("bottom") == (0.5, 1.0)
    assert parse_crop_anchor("left") == (0.0, 0.5)
    assert parse_crop_anchor("right") == (1.0, 0.5)
    assert parse_crop_anchor("0.2, 0.8") == (0.2, 0.8)
    assert parse_crop_anchor((-0.5, 1.5)) == (0.0, 1.0)


def test_fit_to_square_crop_anchor_horizontal():
    # 300x100 image: Left 100px Red, Middle 100px Green, Right 100px Blue
    img = Image.new("RGBA", (300, 100))
    for x in range(100):
        for y in range(100):
            img.putpixel((x, y), (255, 0, 0, 255))
    for x in range(100, 200):
        for y in range(100):
            img.putpixel((x, y), (0, 255, 0, 255))
    for x in range(200, 300):
        for y in range(100):
            img.putpixel((x, y), (0, 0, 255, 255))

    # Left crop
    sq_left = fit_to_square(img, target_size=100, mode=FitMode.CROP, crop_anchor="left")
    assert sq_left.getpixel((50, 50))[:3] == (255, 0, 0)

    # Center crop
    sq_center = fit_to_square(img, target_size=100, mode=FitMode.CROP, crop_anchor="center")
    assert sq_center.getpixel((50, 50))[:3] == (0, 255, 0)

    # Right crop
    sq_right = fit_to_square(img, target_size=100, mode=FitMode.CROP, crop_anchor="right")
    assert sq_right.getpixel((50, 50))[:3] == (0, 0, 255)


def test_fit_to_square_crop_anchor_vertical():
    # 100x300 image: Top 100px Red, Middle 100px Green, Bottom 100px Blue
    img = Image.new("RGBA", (100, 300))
    for x in range(100):
        for y in range(100):
            img.putpixel((x, y), (255, 0, 0, 255))
    for x in range(100):
        for y in range(100, 200):
            img.putpixel((x, y), (0, 255, 0, 255))
    for x in range(100):
        for y in range(200, 300):
            img.putpixel((x, y), (0, 0, 255, 255))

    # Top crop
    sq_top = fit_to_square(img, target_size=100, mode=FitMode.CROP, crop_anchor="top")
    assert sq_top.getpixel((50, 50))[:3] == (255, 0, 0)

    # Center crop
    sq_center = fit_to_square(img, target_size=100, mode=FitMode.CROP, crop_anchor="center")
    assert sq_center.getpixel((50, 50))[:3] == (0, 255, 0)

    # Bottom crop
    sq_bottom = fit_to_square(img, target_size=100, mode=FitMode.CROP, crop_anchor="bottom")
    assert sq_bottom.getpixel((50, 50))[:3] == (0, 0, 255)


def test_normalize_to_rgba():
    rgb_img = Image.new("RGB", (100, 50), color="red")
    rgba_img = normalize_to_rgba(rgb_img)
    assert rgba_img.mode == "RGBA"
    assert rgba_img.size == (100, 50)
    assert rgba_img.getpixel((50, 25)) == (255, 0, 0, 255)


def test_fit_to_square_pad():
    # Wide image 200x100
    img = Image.new("RGBA", (200, 100), color=(255, 0, 0, 255))
    square = fit_to_square(img, target_size=256, mode=FitMode.PAD, margin_ratio=0.0)
    assert square.size == (256, 256)
    assert square.mode == "RGBA"

    # Center pixel must be red
    assert square.getpixel((128, 128))[0] == 255
    # Top border pixel must be transparent (due to letterboxing)
    assert square.getpixel((128, 5))[3] == 0


def test_fit_to_square_crop():
    # Tall image 100x200
    img = Image.new("RGBA", (100, 200), color=(0, 255, 0, 255))
    square = fit_to_square(img, target_size=256, mode=FitMode.CROP, margin_ratio=0.0)
    assert square.size == (256, 256)
    # Center and edges should be filled green
    assert square.getpixel((128, 128))[:3] == (0, 255, 0)
    assert square.getpixel((5, 128))[:3] == (0, 255, 0)


def test_fit_to_square_margin():
    img = Image.new("RGBA", (100, 100), color=(0, 0, 255, 255))
    margin = 0.1  # 10% on each side
    square = fit_to_square(img, target_size=200, mode=FitMode.PAD, margin_ratio=margin)
    assert square.size == (200, 200)
    # Outer 10% (pixel at 5, 5) must be transparent
    assert square.getpixel((5, 5))[3] == 0
    # Center pixel must be blue
    assert square.getpixel((100, 100))[:3] == (0, 0, 255)
