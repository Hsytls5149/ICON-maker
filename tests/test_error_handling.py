"""Unit tests for corrupt file handling, invalid extensions, and error guards."""
import pytest
from pathlib import Path
from src.core.pipeline import IconPipeline


def test_corrupt_file_handling(tmp_path):
    corrupt_file = tmp_path / "corrupted.png"
    # Write garbage data into PNG file
    corrupt_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00GARBAGE_PAYLOAD_NOT_A_VALID_IMAGE")

    pipeline = IconPipeline()
    with pytest.raises(ValueError, match="Failed to read or parse image"):
        pipeline.load_image(corrupt_file)


def test_zero_byte_file_handling(tmp_path):
    empty_file = tmp_path / "empty.png"
    empty_file.write_bytes(b"")

    pipeline = IconPipeline()
    with pytest.raises(ValueError, match="Failed to read or parse image"):
        pipeline.load_image(empty_file)


def test_unsupported_extension_handling(tmp_path):
    text_file = tmp_path / "document.txt"
    text_file.write_text("Hello world")

    pipeline = IconPipeline()
    with pytest.raises(ValueError, match="Unsupported image extension"):
        pipeline.load_image(text_file)


def test_missing_file_handling(tmp_path):
    missing_file = tmp_path / "non_existent.png"
    pipeline = IconPipeline()
    with pytest.raises(FileNotFoundError, match="Input file not found"):
        pipeline.load_image(missing_file)
