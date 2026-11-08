"""Build and packaging script for WinIconStudio."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def build(onefile: bool = False):
    print("=" * 60)
    print(f"Building WinIconStudio ({'OneFile' if onefile else 'OneDir'})...")
    print("=" * 60)

    model_src = ROOT_DIR / "models" / "u2netp.onnx"
    if not model_src.exists():
        print(f"[ERROR] Model file missing: {model_src}", file=sys.stderr)
        sys.exit(1)

    pyinstaller_exe = ROOT_DIR / ".venv" / "Scripts" / "pyinstaller.exe"
    if not pyinstaller_exe.exists():
        pyinstaller_exe = Path(shutil.which("pyinstaller") or "pyinstaller")

    dist_path = ROOT_DIR / "dist" / ("portable" if onefile else "release")

    # Command arguments
    cmd = [
        str(pyinstaller_exe),
        "--noconfirm",
        "--windowed",
        "--name", "WinIconStudio",
        "--distpath", str(dist_path),
        "--add-data", f"{model_src};models",
        "--collect-all", "onnxruntime",
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    cmd.append(str(ROOT_DIR / "main.py"))

    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(ROOT_DIR))

    if not onefile:
        dist_dir = dist_path / "WinIconStudio"
        if dist_dir.exists() and not (dist_dir / "models").exists():
            (dist_dir / "models").mkdir(parents=True, exist_ok=True)
            shutil.copy2(model_src, dist_dir / "models" / "u2netp.onnx")
        print(f"\n[SUCCESS] Build completed! Check '{dist_dir}' folder.")
    else:
        exe_file = dist_path / "WinIconStudio.exe"
        print(f"\n[SUCCESS] Single-file portable executable completed! Check '{exe_file}'.")


if __name__ == "__main__":
    is_onefile = "--onefile" in sys.argv
    build(onefile=is_onefile)
