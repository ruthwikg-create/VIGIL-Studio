"""Headless-safe checks that GUI routes and palette remain loadable.
See scripts/smoke_desktop.py for graphical checks requiring Tk display.
"""
def test_instrument_pages_are_unique_and_complete():
    from vigil_studio.ui.app import NAV_GROUPS,PAGE_META,Studio
    pages=[page for _,items in NAV_GROUPS for page in items]
    assert len(pages)==14
    assert len(set(pages))==len(pages)
    assert set(pages)==set(PAGE_META)
    assert len(set(PAGE_META[name][0] for name in pages))==14
    assert hasattr(Studio,'_set_panels') and hasattr(Studio,'_cursor_event')


def test_trace_channel_colours_are_unique_and_printable():
    from vigil_studio.ui.app import C,CH_COLORS
    assert len(set(CH_COLORS.values()))>=5
    assert all(isinstance(x,str) and len(x)==7 and x.startswith('#') for x in CH_COLORS.values())
    assert C['accent']!=C['blue'] and C['surface']!=C['sidebar']
