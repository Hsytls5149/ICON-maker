"""Multi-scale icon downsampling pyramid with size-calibrated Unsharp Masking."""
from typing import Dict, List, Tuple
from PIL import Image, ImageFilter

# Standard Windows icon sizes in descending order
ICON_SIZES: List[int] = [256, 128, 64, 48, 32, 24, 16]

# Base Unsharp Mask parameters calibrated for micro-resolutions: (radius, percent, threshold)
SIZE_SHARPEN_PROFILES: Dict[int, Tuple[float, int, int]] = {
    16:  (0.8, 180, 2),   # High-pass micro-contrast for taskbar/tray
    24:  (0.9, 160, 2),   # 150% scaling taskbar
    32:  (1.0, 140, 3),   # Standard Explorer detail list
    48:  (1.1, 110, 3),   # Desktop standard tile
    64:  (1.2, 80, 3),    # Medium Explorer tile
    128: (1.3, 50, 4),    # Large preview
    256: (1.5, 25, 4),    # Extra large preview (minimal gentle touch)
}


class IconResampler:
    """
    Downsamples a master square image into the standard Windows icon size pyramid
    with size-bracketed edge enhancement.
    """

    def __init__(self, sharpening_strength: float = 1.0):
        """
        Args:
            sharpening_strength: Multiplier for sharpening intensity (0.0 = disabled, 1.0 = default calibrated).
        """
        self.sharpening_strength = max(0.0, float(sharpening_strength))

    def sharpen_image(self, image: Image.Image, size: int) -> Image.Image:
        """
        Applies calibrated unsharp masking tailored to the specific icon resolution,
        safeguarding the alpha channel from dark halo artifacts.
        """
        if self.sharpening_strength <= 0.01:
            return image

        profile = SIZE_SHARPEN_PROFILES.get(size)
        if not profile:
            # Fallback profile for non-standard size
            profile = (1.0, int(round(100 * (32 / max(16, size)))), 3)

        radius, base_percent, threshold = profile
        effective_percent = int(round(base_percent * self.sharpening_strength))
        if effective_percent <= 0:
            return image

        # Separate RGB and Alpha to avoid edge halos on transparency
        if image.mode == "RGBA":
            r, g, b, a = image.split()
            rgb = Image.merge("RGB", (r, g, b))
            sharpened_rgb = rgb.filter(
                ImageFilter.UnsharpMask(radius=radius, percent=effective_percent, threshold=threshold)
            )
            sr, sg, sb = sharpened_rgb.split()
            return Image.merge("RGBA", (sr, sg, sb, a))
        else:
            return image.filter(
                ImageFilter.UnsharpMask(radius=radius, percent=effective_percent, threshold=threshold)
            )

    def generate_pyramid(
        self,
        master_image: Image.Image,
        sizes: List[int] = ICON_SIZES
    ) -> Dict[int, Image.Image]:
        """
        Generates all standard downsampled and sharpened icon images from a master square.
        
        Args:
            master_image: Master square image (preferably 256x256 or 512x512, RGBA).
            sizes: Target resolutions list. Defaults to ICON_SIZES.
            
        Returns:
            Dictionary mapping size (e.g. 16, 32, ..., 256) to corresponding PIL Image.
        """
        pyramid: Dict[int, Image.Image] = {}

        for size in sizes:
            # Downsample using Lanczos filtering
            resized = master_image.resize((size, size), Image.Resampling.LANCZOS)
            
            # Apply size-bracketed unsharp mask
            sharpened = self.sharpen_image(resized, size)
            pyramid[size] = sharpened

        return pyramid
