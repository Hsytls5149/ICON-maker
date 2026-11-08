Download: [<3](https://github.com/Hsytls5149/ICON-maker/releases/download/1/WinIconStudio.exe)

**WinIconStudio** is a high-performance, offline Windows desktop utility and CLI that converts arbitrary image files (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`) into sharp, professional-grade, multi-resolution `.ico` containers with on-device AI background removal and dynamic edge sharpening.



## Quick Start

### 1. Launch Graphical User Interface (GUI)

```powershell
# Option A: Single-file portable executable (no companion folder, drop anywhere):
.\dist\portable\WinIconStudio.exe

# Option B: Folder-based standalone build:
.\dist\release\WinIconStudio\WinIconStudio.exe

# Option C: Running directly via Python:
.\.venv\Scripts\python.exe main.py
```

### 2. Command-Line Interface (CLI Prototype)

Convert any image directly from the command line:

```powershell
# Basic conversion with transparent padding and default 5% margin
.\.venv\Scripts\python.exe src\cli.py input.png -o output.ico

# Conversion with on-device AI background removal enabled
.\.venv\Scripts\python.exe src\cli.py photo.jpg -o photo.ico --remove-bg --benchmark

# Square crop with top alignment (ideal for character portraits):
.\.venv\Scripts\python.exe src\cli.py portrait.jpg -o portrait.ico --mode crop --crop-anchor top

# Custom aspect fit mode, margin, and sharpening strength
.\.venv\Scripts\python.exe src\cli.py logo.png -o logo.ico --mode pad --margin 0.1 --sharpen 1.2
```

#### CLI Options:
```
positional arguments:
  input                 Path to input image (.png, .jpg, .jpeg, .webp, .bmp)

options:
  -o, --output          Destination path for .ico file (default: <input_stem>.ico)
  --remove-bg           Enable on-device AI background removal
  --mode {pad,crop}     Aspect ratio fit mode: 'pad' (transparent letterbox) or 'crop'
  --crop-anchor ANCHOR  Crop position: 'top', 'bottom', 'left', 'right', 'center', or 'x,y'
  --margin MARGIN       Inner margin ratio (0.0 to 0.4, default: 0.05)
  --sharpen SHARPEN     Sharpening strength multiplier (default: 1.0)
  --sizes SIZES         Comma-separated list of resolutions (default: 16,24,32,48,64,128,256)
  --benchmark           Print step-by-step latency benchmarks
```

---

## Technical Architecture & File Layout

```
ICON/
├── src/
│   ├── core/
│   │   ├── aspect.py         # Aspect ratio normalization (pad vs crop + margin)
│   │   ├── segmenter.py      # On-device AI background removal (u2netp ONNX CPU)
│   │   ├── resampler.py      # Resampling pyramid with dynamic unsharp mask
│   │   ├── ico_writer.py     # Microsoft Windows ICO binary container writer
│   │   └── pipeline.py       # Full pipeline orchestrator
│   ├── gui/
│   │   ├── app.py            # Application launcher & Fluent Windows 11 styling
│   │   ├── main_window.py    # Main window with sidebar controls and layout
│   │   ├── preview_widget.py # Explorer Simulation Matrix and checkerboard canvas
│   │   └── worker.py         # Async QThread worker (zero UI freeze)
│   └── cli.py                # Standalone CLI interface
├── models/
│   └── u2netp.onnx           # Lightweight AI segmentation model (~4.3 MB)
├── installer/
│   └── WinIconStudio.iss     # Inno Setup 6 installer script
├── tests/                    # Automated pytest test suite
│   ├── test_aspect.py
│   ├── test_resampler.py
│   ├── test_ico_writer.py
│   ├── test_segmenter.py
│   ├── test_pipeline.py
│   ├── test_gui.py
│   └── test_error_handling.py
├── build.py                  # PyInstaller build automation script
├── pyproject.toml            # Project configuration and metadata
└── main.py                   # Root executable launcher
```

---

