"""Unit tests for Windows ICO binary container generation."""
import io
import struct
import pytest
from PIL import Image
from src.core.ico_writer import build_ico, write_ico_file
from src.core.resampler import ICON_SIZES


def test_build_ico_structure(tmp_path):
    images = {
        size: Image.new("RGBA", (size, size), color=(size % 256, 120, 200, 255))
        for size in ICON_SIZES
    }

    ico_data = build_ico(images)

    # 1. Verify header (6 bytes)
    id_reserved, id_type, id_count = struct.unpack("<HHH", ico_data[:6])
    assert id_reserved == 0
    assert id_type == 1  # 1 = ICO
    assert id_count == len(ICON_SIZES)

    # 2. Verify directory entries
    offset = 6
    for i, size in enumerate(sorted(ICON_SIZES)):
        entry = ico_data[offset : offset + 16]
        offset += 16
        b_w, b_h, b_colors, b_res, planes, bpp, data_len, img_offset = struct.unpack("<BBBBHHII", entry)

        expected_w = 0 if size == 256 else size
        expected_h = 0 if size == 256 else size
        assert b_w == expected_w
        assert b_h == expected_h
        assert planes == 1
        assert bpp == 32
        assert data_len > 0
        assert img_offset >= 6 + 16 * len(ICON_SIZES)

        payload = ico_data[img_offset : img_offset + data_len]
        if size == 256:
            # Must be valid PNG
            assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        else:
            # Must be valid DIB header (biSize=40, biWidth=size, biHeight=size*2)
            bi_size, bi_w, bi_h, bi_planes, bi_bpp = struct.unpack("<IIIHH", payload[:16])
            assert bi_size == 40
            assert bi_w == size
            assert bi_h == size * 2
            assert bi_planes == 1
            assert bi_bpp == 32

    # 3. Verify PIL can open and parse the generated ICO
    output_ico = tmp_path / "test.ico"
    output_ico.write_bytes(ico_data)
    with Image.open(output_ico) as img:
        assert img.format == "ICO"
        assert img.size == (16, 16) or img.size == (256, 256)
