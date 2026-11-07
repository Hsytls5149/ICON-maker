"""End-to-end icon processing pipeline connecting ingestion, segmentation, fitting, and export."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from PIL import Image

from src.core.aspect import fit_to_square, normalize_to_rgba, FitMode
from src.core.segmenter import BackgroundSegmenter
from src.core.resampler import IconResampler, ICON_SIZES
from src.core.ico_writer import build_ico, write_ico_file

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass
class PipelineOptions:
    """Configurable parameters for icon generation."""
    fit_mode: FitMode = FitMode.PAD
    margin_ratio: float = 0.05
    remove_background: bool = False
    sharpening_strength: float = 1.0
    sizes: List[int] = field(default_factory=lambda: list(ICON_SIZES))
    crop_anchor: Tuple[float, float] = (0.5, 0.5)


@dataclass
class PipelineResult:
    """Output artifacts of a completed pipeline run."""
    raw_image: Image.Image
    segmented_image: Optional[Image.Image]
    master_square: Image.Image
    pyramid: Dict[int, Image.Image]
    ico_bytes: bytes


class IconPipeline:
    """Orchestrates image transformation and ICO packaging."""

    def __init__(self, segmenter: Optional[BackgroundSegmenter] = None):
        self.segmenter = segmenter or BackgroundSegmenter()

    @staticmethod
    def load_image(source: Union[str, Path, Image.Image]) -> Image.Image:
        """
        Loads and validates an image from a path or passes through a PIL Image.
        
        Raises:
            FileNotFoundError: If the path does not exist.
            ValueError: If the file format is unsupported or corrupted.
        """
        if isinstance(source, Image.Image):
            return normalize_to_rgba(source)

        path = Path(source).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported image extension '{path.suffix}'. "
                f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        try:
            with Image.open(path) as img:
                img.load()
                return normalize_to_rgba(img)
        except Exception as e:
            raise ValueError(f"Failed to read or parse image '{path.name}': {e}") from e

    def process(
        self,
        source: Union[str, Path, Image.Image],
        options: Optional[PipelineOptions] = None
    ) -> PipelineResult:
        """
        Executes the full icon generation workflow.
        
        Args:
            source: Image path or PIL Image object.
            options: Configuration options.
            
        Returns:
            PipelineResult containing master square, pyramid, and ICO bytes.
        """
        if options is None:
            options = PipelineOptions()

        raw_img = self.load_image(source)

        # Step 1: Optional AI Background Removal
        segmented_img: Optional[Image.Image] = None
        current_img = raw_img

        if options.remove_background:
            segmented_img = self.segmenter.remove_background(raw_img)
            current_img = segmented_img

        # Step 2: Square Aspect Ratio & Padding Normalization (512x512 master)
        master_square = fit_to_square(
            image=current_img,
            target_size=512,
            mode=options.fit_mode,
            margin_ratio=options.margin_ratio,
            crop_anchor=options.crop_anchor
        )

        # Step 3: Downsampling Pyramid with Size-Calibrated Sharpening
        resampler = IconResampler(sharpening_strength=options.sharpening_strength)
        pyramid = resampler.generate_pyramid(master_square, sizes=options.sizes)

        # Step 4: Multi-Resolution Windows ICO Packaging
        ico_bytes = build_ico(pyramid, sizes=options.sizes)

        return PipelineResult(
            raw_image=raw_img,
            segmented_image=segmented_img,
            master_square=master_square,
            pyramid=pyramid,
            ico_bytes=ico_bytes
        )

    def export(
        self,
        source: Union[str, Path, Image.Image],
        output_path: Union[str, Path],
        options: Optional[PipelineOptions] = None
    ) -> Path:
        """Processes the image and writes the .ico file directly to disk."""
        result = self.process(source, options)
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(result.ico_bytes)
        return out
