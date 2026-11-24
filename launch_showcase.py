"""Launch actual VIGIL Studio 4.8 in a separate, synthetic showcase workspace."""
from pathlib import Path
import os
root=Path(__file__).resolve().parent/'SHOWCASE'
# Keep demo display preference separate from real settings.
os.environ['APPDATA']=str(root/'showcase_preferences')
os.environ['XDG_CONFIG_HOME']=str(root/'showcase_preferences')
from scripts.seed_showcase_workspace import build
from vigil_studio.ui.app import Studio
if __name__=='__main__':
    workspace=root/'demo_workspace'
    ws,ids=build(workspace)
    app=Studio(workspace_path=workspace)
    app.load_case(ids['SYNTHETIC_BASELINE'])
    app.show('Overview')
    app.mainloop()
