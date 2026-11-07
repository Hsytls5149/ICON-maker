"""Aspect ratio transformation and canvas fitting for square icons."""
from enum import Enum
from typing import Tuple, Union, Dict
from PIL import Image, ImageOps


class FitMode(str, Enum):
    """Aspect ratio normalization mode."""
    PAD = "pad"    # Transparent letterbox / pillarbox (preserves entire subject)
    CROP = "crop"  # Crop to square with configurable anchor alignment


CROP_ANCHOR_PRESETS: Dict[str, Tuple[float, float]] = {
    "center": (0.5, 0.5),
    "top": (0.5, 0.0),
    "bottom": (0.5, 1.0),
    "left": (0.0, 0.5),
    "right": (1.0, 0.5),
    "top-left": (0.0, 0.0),
    "top-right": (1.0, 0.0),
    "bottom-left": (0.0, 1.0),
    "bottom-right": (1.0, 1.0),
}


def parse_crop_anchor(anchor: Union[str, Tuple[float, float]]) -> Tuple[float, float]:
    """
    Parses a crop anchor into (x, y) coordinates normalized between 0.0 and 1.0.
    
    Accepts preset names ('center', 'top', 'bottom', 'left', 'right', etc.)
    or coordinate tuples/strings like '0.2,0.8'.
    """
    if isinstance(anchor, str):
        key = anchor.strip().lower()
        if key in CROP_ANCHOR_PRESETS:
            return CROP_ANCHOR_PRESETS[key]
        if "," in key:
            try:
                parts = key.split(",")
                ax = float(parts[0].strip())
                ay = float(parts[1].strip())
                return (max(0.0, min(1.0, ax)), max(0.0, min(1.0, ay)))
            except Exception:
                pass
        return (0.5, 0.5)

    if isinstance(anchor, (tuple, list)) and len(anchor) >= 2:
        ax = max(0.0, min(1.0, float(anchor[0])))
        ay = max(0.0, min(1.0, float(anchor[1])))
        return (ax, ay)

    return (0.5, 0.5)


def normalize_to_rgba(image: Image.Image) -> Image.Image:
    """Normalize any PIL image mode to 32-bit RGBA without color shift."""
    if image.mode == "RGBA":
        return image.copy()
    
    # Handle palette with transparency
    if image.mode == "P":
        return image.convert("RGBA")
    
    # Handle grayscale with alpha
    if image.mode == "LA":
        return image.convert("RGBA")
        
    # Auto-orient based on EXIF if present
    try:
        oriented = ImageOps.exif_transpose(image)
        if oriented is not None:
            image = oriented
    except Exception:
        pass
        
    return image.convert("RGBA")


def fit_to_square(
    image: Image.Image,
    target_size: int = 512,
    mode: Union[FitMode, str] = FitMode.PAD,
    margin_ratio: float = 0.0,
    background_color: Tuple[int, int, int, int] = (0, 0, 0, 0),
    crop_anchor: Union[Tuple[float, float], str] = (0.5, 0.5)
) -> Image.Image:
    """
    Fits an arbitrary aspect ratio image into a square canvas.
    
    Args:
        image: Source PIL image.
        target_size: Dimension of the output square canvas (width and height).
        mode: FitMode.PAD (letterbox/pillarbox) or FitMode.CROP (crop to square).
        margin_ratio: Inset margin ratio (0.0 to 0.45) applied inside canvas.
        background_color: RGBA background tuple. Defaults to transparent.
        crop_anchor: (x, y) normalized alignment (0.0 to 1.0) or preset string when cropping.
        
    Returns:
        Square PIL Image in RGBA format.
    """
    if isinstance(mode, str):
        mode = FitMode(mode.lower())

    img = normalize_to_rgba(image)
    orig_w, orig_h = img.size
    
    if orig_w <= 0 or orig_h <= 0:
        raise ValueError(f"Invalid image dimensions: {orig_w}x{orig_h}")
        
    # Clamp margin ratio between 0.0 and 0.45
    margin_ratio = max(0.0, min(0.45, float(margin_ratio)))
    
    # Usable canvas inside the margin
    usable_size = int(round(target_size * (1.0 - 2.0 * margin_ratio)))
    usable_size = max(16, usable_size)
    
    if mode == FitMode.CROP:
        # Scale image such that the smaller dimension matches usable_size, then crop according to anchor
        scale = max(usable_size / orig_w, usable_size / orig_h)
        new_w = max(1, int(round(orig_w * scale)))
        new_h = max(1, int(round(orig_h * scale)))
        
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        anchor_x, anchor_y = parse_crop_anchor(crop_anchor)
        max_shift_x = max(0, new_w - usable_size)
        max_shift_y = max(0, new_h - usable_size)

        crop_left = int(round(max_shift_x * anchor_x)) if max_shift_x > 0 else 0
        crop_top = int(round(max_shift_y * anchor_y)) if max_shift_y > 0 else 0

        crop_left = max(0, min(max_shift_x, crop_left))
        crop_top = max(0, min(max_shift_y, crop_top))

        cropped = resized.crop((crop_left, crop_top, crop_left + usable_size, crop_top + usable_size))
        
        # Create final square canvas
        canvas = Image.new("RGBA", (target_size, target_size), background_color)
        paste_x = (target_size - usable_size) // 2
        paste_y = (target_size - usable_size) // 2
        canvas.paste(cropped, (paste_x, paste_y), cropped)
        return canvas

    else:  # FitMode.PAD
        # Scale image such that the larger dimension matches usable_size
        scale = min(usable_size / orig_w, usable_size / orig_h)
        new_w = max(1, int(round(orig_w * scale)))
        new_h = max(1, int(round(orig_h * scale)))
        
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        canvas = Image.new("RGBA", (target_size, target_size), background_color)
        paste_x = (target_size - new_w) // 2
        paste_y = (target_size - new_h) // 2
        canvas.paste(resized, (paste_x, paste_y), resized)
        return canvas
