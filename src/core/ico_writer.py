"""Windows multi-resolution ICO container builder and writer.

Implements official Microsoft Windows Shell ICO specifications:
- 256x256: PNG-compressed sub-stream (Vista+ standard)
- 16x16 to 128x128: 32-bit BGRA uncompressed DIB (XOR mask + 1-bit AND mask)
- Correct biHeight doubling and DWORD row padding
"""
import io
import struct
from pathlib import Path
from typing import Dict, List, Optional, Union
import numpy as np
from PIL import Image

from src.core.resampler import ICON_SIZES


def _encode_png_stream(image: Image.Image) -> bytes:
    """Encode an image as a memory-optimized PNG sub-stream."""
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _encode_dib_stream(image: Image.Image) -> bytes:
    """
    Encode an image as a 32-bit BGRA DIB with BITMAPINFOHEADER, XOR mask,
    and 1-bit monochrome AND mask padded to 32-bit boundaries.
    """
    w, h = image.size
    rgba = image.convert("RGBA")
    arr = np.array(rgba, dtype=np.uint8)  # (h, w, 4): R, G, B, A

    # XOR mask: 32-bit BGRA, stored bottom-up
    # Flip vertically to make bottom-up
    bottom_up = np.flipud(arr)
    # Reorder channels: R, G, B, A -> B, G, R, A
    bgra = bottom_up[:, :, [2, 1, 0, 3]]
    xor_bytes = bgra.tobytes()

    # AND mask: 1 bit per pixel, bottom-up, padded to 32-bit (4-byte) boundary per row
    # 0 = opaque, 1 = transparent
    alpha_bottom_up = bottom_up[:, :, 3]
    and_mask_rows: List[bytes] = []
    row_stride = ((w + 31) // 32) * 4  # DWORD aligned

    for y in range(h):
        row_alpha = alpha_bottom_up[y, :]
        row_bits = bytearray(row_stride)
        for x in range(w):
            if row_alpha[x] < 128:  # Transparent pixel
                byte_idx = x // 8
                bit_idx = 7 - (x % 8)
                row_bits[byte_idx] |= (1 << bit_idx)
        and_mask_rows.append(bytes(row_bits))

    and_bytes = b"".join(and_mask_rows)

    # BITMAPINFOHEADER (40 bytes)
    bi_size = 40
    bi_width = w
    bi_height = h * 2  # Mandatory in ICO specs: XOR height + AND height
    bi_planes = 1
    bi_bit_count = 32
    bi_compression = 0  # BI_RGB
    bi_size_image = len(xor_bytes) + len(and_bytes)
    bi_x_pels = 0
    bi_y_pels = 0
    bi_clr_used = 0
    bi_clr_important = 0

    header = struct.pack(
        "<IIIHHIIIIII",
        bi_size,
        bi_width,
        bi_height,
        bi_planes,
        bi_bit_count,
        bi_compression,
        bi_size_image,
        bi_x_pels,
        bi_y_pels,
        bi_clr_used,
        bi_clr_important,
    )

    return header + xor_bytes + and_bytes


def build_ico(images: Dict[int, Image.Image], sizes: Optional[List[int]] = None) -> bytes:
    """
    Builds a compliant Windows multi-resolution ICO binary container.

    Args:
        images: Mapping of icon size to PIL Image.
        sizes: Ordered list of sizes to include. Defaults to ascending or descending ICON_SIZES.

    Returns:
        Raw bytes of the complete .ico file.
    """
    if sizes is None:
        # Standard order: ascending or descending. Windows Shell works best with descending or ascending.
        # Ascending (16, 24, 32, 48, 64, 128, 256) is standard for many tools.
        sizes = sorted([s for s in images.keys() if s in images])

    if not sizes:
        raise ValueError("At least one icon image must be provided to build an ICO file.")

    num_images = len(sizes)
    # Header: idReserved (0), idType (1 for icon), idCount (number of images)
    header = struct.pack("<HHH", 0, 1, num_images)

    # Prepare encoded image data payloads
    encoded_payloads: List[bytes] = []
    entries_meta: List[Dict[str, int]] = []

    for size in sizes:
        img = images[size]
        if size >= 256:
            # 256px uses PNG compression
            payload = _encode_png_stream(img)
            b_w = 0  # 0 indicates 256
            b_h = 0
        else:
            # 16-128px uses 32-bit DIB
            payload = _encode_dib_stream(img)
            b_w = size
            b_h = size

        encoded_payloads.append(payload)
        entries_meta.append({
            "bWidth": b_w,
            "bHeight": b_h,
            "bColorCount": 0,
            "bReserved": 0,
            "wPlanes": 1,
            "wBitCount": 32,
            "dwBytesInRes": len(payload),
        })

    # Calculate offsets
    # Directory starts immediately after header (6 bytes)
    # Each entry is 16 bytes
    directory_size = 16 * num_images
    current_offset = 6 + directory_size

    directory_entries: List[bytes] = []
    for meta, payload in zip(entries_meta, encoded_payloads):
        entry_bytes = struct.pack(
            "<BBBBHHII",
            meta["bWidth"],
            meta["bHeight"],
            meta["bColorCount"],
            meta["bReserved"],
            meta["wPlanes"],
            meta["wBitCount"],
            meta["dwBytesInRes"],
            current_offset,
        )
        directory_entries.append(entry_bytes)
        current_offset += len(payload)

    return header + b"".join(directory_entries) + b"".join(encoded_payloads)


def write_ico_file(
    images: Dict[int, Image.Image],
    output_path: Union[str, Path],
    sizes: Optional[List[int]] = None
) -> Path:
    """
    Builds and writes a compliant multi-resolution ICO file to disk.

    Args:
        images: Mapping of icon size to PIL Image.
        output_path: Destination file path (.ico).
        sizes: List of sizes to include.

    Returns:
        Path to the saved .ico file.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    ico_bytes = build_ico(images, sizes)
    path.write_bytes(ico_bytes)
    return path
