"""Regression checks for v4.3 sidebar ordering and workspace layout routes."""
from vigil_studio.ui.app import Studio,NAV_GROUPS,PAGE_META


def test_navigation_numerical_order_and_sections():
    pages=[page for _,items in NAV_GROUPS for page in items]
    assert len(pages)==14
    assert [int(PAGE_META[name][0]) for name in pages]==list(range(1,15))
    assert pages[11:]==['Guide & Safety','ECG Validation','Settings']
    assert all(len(items)>0 for _,items in NAV_GROUPS)


def test_responsive_layout_methods_exist():
    for name in ('_adapt_overview','_on_window_resize','_adapt_command','_refresh_nav_scroll',
                 '_ensure_nav_visible','_bind_responsive_wrap','_set_sidebar_type_size'):
        assert callable(getattr(Studio,name))


def test_research_routes_not_removed():
    for page,handler in [('ECG Validation','_ecg_validation'),('Signal Lab','_signals'),
                         ('Quality Explorer','_quality'),('Annotation Studio','_annotation_studio')]:
        assert page in PAGE_META
        assert callable(getattr(Studio,handler))
