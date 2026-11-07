"""Core image processing and icon generation modules."""
from src.core.aspect import fit_to_square, FitMode, parse_crop_anchor, CROP_ANCHOR_PRESETS
from src.core.segmenter import BackgroundSegmenter
from src.core.resampler import IconResampler, ICON_SIZES
from src.core.ico_writer import build_ico, write_ico_file
from src.core.pipeline import IconPipeline, PipelineOptions

__all__ = [
    "fit_to_square",
    "FitMode",
    "parse_crop_anchor",
    "CROP_ANCHOR_PRESETS",
    "BackgroundSegmenter",
    "IconResampler",
    "ICON_SIZES",
    "build_ico",
    "write_ico_file",
    "IconPipeline",
    "PipelineOptions",
]
