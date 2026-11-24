"""Graphical smoke against a temporary test workspace (no clinical data)."""
import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vigil_studio.ui.app import Studio,PAGE_META
from PIL import ImageGrab

def main():
    with tempfile.TemporaryDirectory(prefix='vigil46_test_') as td:
        os.environ['APPDATA']=str(Path(td)/'settings')
        os.environ['XDG_CONFIG_HOME']=str(Path(td)/'settings')
        app=Studio(workspace_path=Path(td)/'workspace')
        errors=[]
        app.report_callback_exception=lambda typ,err,tb:errors.append(f'{typ.__name__}: {err}')
        try:
            assert '4.7' in app.title() and 'Ruthwik Goparaju' in app.title()
            app.geometry('1500x900+0+0')
            for page in PAGE_META:
                app.show(page)
                app.update_idletasks();app.update()
            app._set_sidebar_type_size(16)
            app.show('Guide & Safety')
            for _ in range(3):app.update()
            assert not errors,errors
            # Capture actual GUI only if the image server supports screenshots.
            out=ROOT/'examples'/'HOSPITAL_READINESS_GUI_V4_7.png'
            ImageGrab.grab(bbox=(0,0,1500,900)).save(out)
            print('GUI PASS: all',len(PAGE_META),'sections, Guide & Safety and enlarged sidebar, image',out)
        finally:
            app._close_window()
if __name__=='__main__':main()
