"""Command-Line Interface (CLI) for WinIconStudio (Sprint 1 Prototype)."""
import argparse
import sys
import time
from pathlib import Path

# Ensure root package is in sys.path when running as a script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.aspect import FitMode, parse_crop_anchor, CROP_ANCHOR_PRESETS
from src.core.pipeline import IconPipeline, PipelineOptions
from src.core.resampler import ICON_SIZES


def main():
    parser = argparse.ArgumentParser(
        description="WinIconStudio CLI - High-Fidelity Windows .ico Generator with AI Background Removal"
    )
    parser.add_argument("input", help="Path to input image (.png, .jpg, .jpeg, .webp, .bmp)")
    parser.add_argument("-o", "--output", help="Destination path for .ico file (default: <input_stem>.ico)")
    parser.add_argument("--remove-bg", action="store_true", help="Enable on-device AI background removal")
    parser.add_argument(
        "--mode",
        choices=["pad", "crop"],
        default="pad",
        help="Aspect ratio fit mode: 'pad' (transparent letterbox) or 'crop' (square crop)"
    )
    parser.add_argument(
        "--crop-anchor",
        type=str,
        default="center",
        help=(
            "Crop position alignment when using --mode crop. "
            "Presets: 'center', 'top', 'bottom', 'left', 'right', 'top-left', 'top-right', 'bottom-left', 'bottom-right', "
            "or normalized coordinates 'x,y' (0.0 to 1.0, default: 'center')"
        )
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=0.05,
        help="Inner margin padding ratio inside the square canvas (0.0 to 0.4, default: 0.05)"
    )
    parser.add_argument(
        "--sharpen",
        type=float,
        default=1.0,
        help="Sharpening strength multiplier (0.0 = disabled, 1.0 = calibrated, default: 1.0)"
    )
    parser.add_argument(
        "--sizes",
        type=str,
        default=",".join(str(s) for s in ICON_SIZES),
        help=f"Comma-separated list of resolutions (default: {','.join(str(s) for s in ICON_SIZES)})"
    )
    parser.add_argument("--benchmark", action="store_true", help="Print step-by-step latency benchmarks")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] Input file does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".ico")

    try:
        sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]
    except ValueError:
        print("[ERROR] Invalid sizes specified. Must be comma-separated integers.", file=sys.stderr)
        sys.exit(1)

    crop_coords = parse_crop_anchor(args.crop_anchor)

    options = PipelineOptions(
        fit_mode=FitMode(args.mode),
        margin_ratio=args.margin,
        remove_background=args.remove_bg,
        sharpening_strength=args.sharpen,
        sizes=sizes,
        crop_anchor=crop_coords,
    )

    print(f"[*] Processing '{input_path.name}' -> '{output_path.name}'")
    print(f"    Mode: {options.fit_mode.value.upper()} | Margin: {options.margin_ratio * 100:.1f}%")
    if options.fit_mode == FitMode.CROP:
        print(f"    Crop Anchor: {args.crop_anchor} -> ({crop_coords[0]:.2f}, {crop_coords[1]:.2f})")
    print(f"    AI Background Removal: {'ENABLED' if options.remove_background else 'DISABLED'}")
    print(f"    Sharpening Multiplier: {options.sharpening_strength}x | Target Sizes: {options.sizes}")

    pipeline = IconPipeline()
    t0 = time.perf_counter()

    try:
        result = pipeline.process(input_path, options)
    except Exception as e:
        print(f"[ERROR] Pipeline failed: {e}", file=sys.stderr)
        sys.exit(2)

    t_proc = time.perf_counter() - t0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result.ico_bytes)
    total_time = time.perf_counter() - t0

    print(f"[SUCCESS] Generated '{output_path.name}' ({len(result.ico_bytes):,} bytes)")
    if args.benchmark:
        print(f"    Processing Latency: {t_proc * 1000:.1f} ms")
        print(f"    Total Wall Clock:   {total_time * 1000:.1f} ms")


if __name__ == "__main__":
    main()
