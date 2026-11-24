"""Regression tests for user-provided signal logo and application identity."""
from pathlib import Path
from PIL import Image
from vigil_studio.ui import branding
from vigil_studio.ui.app import Studio
from vigil_studio import __version__


def test_logo_assets_are_real_and_transparent():
    assets=branding.assets_directory()
    for name in ('vigil_full_logo_original.png','vigil_signal_sidebar.png','vigil_signal_icon.png','vigil_signal_icon.ico'):
        assert (assets/name).is_file(), name
    full=Image.open(assets/'vigil_full_logo_original.png')
    assert full.size==(2047,682)
    icon=Image.open(assets/'vigil_signal_icon.png')
    assert icon.size==(256,256)
    assert icon.mode=='RGBA'
    assert icon.getpixel((0,0))[3]==0


def test_branding_helpers_and_versions():
    assert callable(branding.sidebar_icon)
    assert callable(branding.apply_window_icon)
    assert __version__=='4.8.0'
    assert hasattr(Studio,'_set_sidebar_type_size')


def test_window_title_and_ui_uses_correct_logo():
    source=Path(Studio.__module__.replace('.', '/')+'.py')
    if not source.is_file():
        source=Path(__file__).resolve().parents[1]/'vigil_studio/ui/app.py'
    text=source.read_text(encoding='utf8')
    assert 'Developed By Ruthwik Goparaju' in text
    assert 'apply_window_icon(self)' in text
    assert 'self._sidebar_brand_image=sidebar_icon()' in text
    assert "text='V /'" not in text
