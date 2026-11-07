"""WinIconStudio root launcher.

Launches modern GUI by default, or CLI if subcommands / arguments are provided.
"""
import os
import sys
import io
from pathlib import Path

# Ensure root package is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _ensure_console_streams():
    """Attach to parent console on Windows if invoked from terminal in windowed mode."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.AttachConsole(-1)
            if sys.stdout is None or getattr(sys.stdout, "closed", False):
                sys.stdout = io.TextIOWrapper(open(r"\\.\CONOUT$", "wb"), encoding="utf-8", write_through=True)
            if sys.stderr is None or getattr(sys.stderr, "closed", False):
                sys.stderr = io.TextIOWrapper(open(r"\\.\CONOUT$", "wb"), encoding="utf-8", write_through=True)
        except Exception:
            pass


if __name__ == "__main__":
    cli_flags = {"-o", "--output", "--remove-bg", "--mode", "--crop-anchor", "--margin", "--sharpen", "--sizes", "--benchmark", "-h", "--help"}
    if any(arg in cli_flags for arg in sys.argv[1:]):
        _ensure_console_streams()
        from src.cli import main as cli_main
        cli_main()
    else:
        from src.gui.app import main as gui_main
        gui_main()
