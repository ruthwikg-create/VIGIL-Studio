"""Local, non-clinical VIGIL Studio display preferences.

Preferences are stored separately from the project source and research database.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

MIN_SIDEBAR_FONT = 9
MAX_SIDEBAR_FONT = 18
DEFAULT_SIDEBAR_FONT = 11


def preference_path() -> Path:
    if os.name == 'nt':
        home = Path(os.environ.get('APPDATA') or (Path.home() / 'AppData' / 'Roaming'))
    else:
        home = Path(os.environ.get('XDG_CONFIG_HOME') or (Path.home() / '.config'))
    return home / 'VIGILStudio' / 'settings.json'


def normalize_sidebar_size(value: object) -> int:
    """Reject invalid/out-of-range saved preferences, never trust JSON inputs."""
    if isinstance(value, bool):
        return DEFAULT_SIDEBAR_FONT
    try:
        size = int(value)
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_SIDEBAR_FONT
    return size if MIN_SIDEBAR_FONT <= size <= MAX_SIDEBAR_FONT else DEFAULT_SIDEBAR_FONT


def load_preferences(path: str | Path | None = None) -> dict:
    path = Path(path) if path is not None else preference_path()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Preference document must be an object')
    except (OSError, ValueError, UnicodeError, TypeError):
        data = {}
    return {'sidebar_font_size': normalize_sidebar_size(data.get('sidebar_font_size'))}


def save_preferences(size: object, path: str | Path | None = None) -> Path:
    path = Path(path) if path is not None else preference_path()
    value = normalize_sidebar_size(size)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement; never truncate an existing settings file on failure.
    import tempfile
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.settings-', suffix='.tmp', delete=False) as f:
            tmp = Path(f.name)
            json.dump({'version': 1, 'sidebar_font_size': value}, f, indent=2)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return path
