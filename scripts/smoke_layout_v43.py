"""Interactive Tk layout verification, with isolated temporary settings and workspace.

Run from the project directory:
    python scripts/smoke_layout_v43.py

Requires a graphical desktop; never opens or modifies a user's research database.
"""
from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vigil_studio.ui.app import Studio,NAV_GROUPS,PAGE_META


def main():
    with tempfile.TemporaryDirectory(prefix='vigil_layout_smoke_') as t:
        config=Path(t)/'settings'
        os.environ['APPDATA']=str(config)
        os.environ['XDG_CONFIG_HOME']=str(config)
        app=Studio(workspace_path=str(Path(t)/'workspace'))
        errors=[]
        app.report_callback_exception=lambda ty,err,tb:errors.append(str(err))
        pages=[page for _,items in NAV_GROUPS for page in items]
        assert [int(PAGE_META[p][0]) for p in pages]==list(range(1,15))
        try:
            for width,height,size in ((1650,900,11),(1650,900,15),(1120,720,18),(1280,800,9)):
                app.geometry(f'{width}x{height}+0+0')
                app._set_sidebar_type_size(size)
                app.show('Overview')
                for _ in range(4):app.update()
                assert app.container.winfo_rootx() >= app.sidebar.winfo_rootx()+app.sidebar.winfo_width()-2
                assert app.heading.winfo_rootx() >= app.container.winfo_rootx()+15
                app._adapt_overview();app.update()
                assert len(app._overview_splitter.panes())==(3 if app.winfo_width()-app.sidebar.winfo_width()-45>=930 else 2)
                if size==18:
                    app.show('Settings');app.update();app._ensure_nav_visible('Settings');app.update()
                    _,item,_=app.nav['Settings']
                    assert item.winfo_rooty() >= app.nav_canvas.winfo_rooty()-2
                    assert item.winfo_rooty()+item.winfo_height() <= app.nav_canvas.winfo_rooty()+app.nav_canvas.winfo_height()+2
            app.geometry('1120x720+0+0')
            app._set_sidebar_type_size(18)
            for page in pages:
                app.show(page);app.update()
            app.show('Settings');app.update()
            app.sidebar_scale.set(16);app.update()
            app.after(450,app.quit);app.mainloop()
            from vigil_studio.ui.preferences import load_preferences
            assert load_preferences()['sidebar_font_size']==16
        finally:
            app._close_window()
        if errors:raise RuntimeError('Tk callbacks failed: '+'; '.join(errors))
        print('PASS: all 14 pages, ordered navigation, 4 screen/font combinations, active-item scrolling and saved preference')


if __name__=='__main__':
    main()
