"""Brand assets: resized from the user-provided VIGIL Studio waveform logo."""
from __future__ import annotations
from pathlib import Path
import sys
import tkinter as tk


def assets_directory() -> Path:
    """Find bundled resources both in source checkout and PyInstaller builds."""
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
    return root / 'vigil_studio' / 'assets'


def apply_window_icon(window: tk.Tk) -> None:
    """Install the supplied signal icon instead of the default Tcl/Tk feather."""
    folder=assets_directory()
    # Keep a PhotoImage reference for Tk's lifetime.
    window._vigil_title_icon = tk.PhotoImage(file=str(folder / 'vigil_signal_icon.png'))
    window.iconphoto(True, window._vigil_title_icon)
    if sys.platform == 'win32':
        try:
            window.iconbitmap(str(folder / 'vigil_signal_icon.ico'))
        except tk.TclError:
            pass  # iconphoto still provides the application icon


def sidebar_icon() -> tk.PhotoImage:
    """A display-sized source-faithful mark; scaling is precomputed with Lanczos."""
    return tk.PhotoImage(file=str(assets_directory() / 'vigil_signal_sidebar.png')).subsample(2,2)
