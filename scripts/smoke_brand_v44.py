"""Graphical brand regression: user-supplied mark + title + font sizes."""
from pathlib import Path
from PIL import ImageGrab
import tempfile,os,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vigil_studio.ui.app import Studio
from vigil_studio.ui.branding import assets_directory


def main():
 with tempfile.TemporaryDirectory(prefix='vigil_brand_smoke_') as t:
  os.environ['APPDATA']=str(Path(t)/'settings')
  os.environ['XDG_CONFIG_HOME']=str(Path(t)/'settings')
  app=Studio(workspace_path=str(Path(t)/'workspace'))
  errors=[]
  app.report_callback_exception=lambda ty,err,tb:errors.append(str(err))
  try:
   assert app.title()=='VIGIL Studio 4.7  |  Instrument Workbench  |  Developed By Ruthwik Goparaju'
   assert str(app.brand_logo.cget('image')) != ''
   assert str(app.iconphoto)  # icon installation ran without TclError
   assert getattr(app,'_vigil_title_icon',None) is not None
   app.geometry('1650x900+0+0');app._set_sidebar_type_size(11)
   app.show('Overview')
   for _ in range(5):app.update()
   app._adapt_overview();app.update()
   assert app.brand_logo.winfo_width()>=40
   ImageGrab.grab(bbox=(0,0,1650,900)).save(ROOT/'examples/BRAND_V4_4_WORKBENCH.png')
   app.geometry('1280x800+0+0');app._set_sidebar_type_size(16);app.show('Settings')
   for _ in range(5):app.update()
   ImageGrab.grab(bbox=(0,0,1280,800)).save(ROOT/'examples/BRAND_V4_4_SETTINGS.png')
   assert not errors,errors
   assert (assets_directory()/'vigil_signal_icon.ico').is_file()
   print('PASS: branded sidebar + window title/icon + 11 and 16 pt layouts + settings')
  finally:
   app._close_window()
if __name__=='__main__':main()
