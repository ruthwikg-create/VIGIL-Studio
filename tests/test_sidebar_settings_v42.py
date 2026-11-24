"""Persistent accessibility preferences, independent of research case storage."""
import json

from vigil_studio.ui.preferences import (
    load_preferences, save_preferences, normalize_sidebar_size,
    MIN_SIDEBAR_FONT, MAX_SIDEBAR_FONT, DEFAULT_SIDEBAR_FONT,
)


def test_user_font_size_ranges():
    assert (MIN_SIDEBAR_FONT, MAX_SIDEBAR_FONT, DEFAULT_SIDEBAR_FONT) == (9,18,11)
    assert normalize_sidebar_size(18)==18
    assert normalize_sidebar_size('13')==13
    for invalid in (-5,40,True,None,'hello',float('nan')):
        assert normalize_sidebar_size(invalid)==11


def test_load_save_persistence(tmp_path):
    path=tmp_path/'prefs'/'settings.json'
    assert load_preferences(path)=={'sidebar_font_size':11}
    assert save_preferences(17,path)==path
    assert load_preferences(path)=={'sidebar_font_size':17}
    assert json.loads(path.read_text())['version']==1
    save_preferences(9,path)
    assert load_preferences(path)['sidebar_font_size']==9


def test_corrupt_preferences_use_default(tmp_path):
    path=tmp_path/'settings.json'
    path.write_text('{invalid',encoding='utf8')
    assert load_preferences(path)['sidebar_font_size']==11
    path.write_text(json.dumps({'sidebar_font_size':1000}),encoding='utf8')
    assert load_preferences(path)['sidebar_font_size']==11
    path.write_text(json.dumps(['bad']),encoding='utf8')
    assert load_preferences(path)['sidebar_font_size']==11


def test_settings_location_can_use_xdg(tmp_path,monkeypatch):
    from vigil_studio.ui.preferences import preference_path
    import os
    monkeypatch.setenv('XDG_CONFIG_HOME',str(tmp_path/'config'))
    if os.name != 'nt':
        assert preference_path()==tmp_path/'config'/'VIGILStudio'/'settings.json'


def test_settings_page_is_accessible():
    from vigil_studio.ui.app import Studio,NAV_GROUPS,PAGE_META
    pages=[n for _,items in NAV_GROUPS for n in items]
    assert len(pages)==14
    assert 'Settings' in pages and 'ECG Validation' in pages
    assert PAGE_META['Settings'][0]=='14'
    assert callable(getattr(Studio,'_settings_page'))
    assert callable(getattr(Studio,'_set_sidebar_type_size'))
