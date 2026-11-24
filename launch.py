"""VIGIL Studio launcher. Does not start network services or patient monitoring."""
import os,sys
from pathlib import Path
from vigil_studio.ui.app import launch

def configured_workspace():
    path=os.environ.get('VIGIL_STUDIO_WORKSPACE')
    if path:return path
    config=Path(__file__).resolve().parent/'VIGIL_WORKSPACE_PATH.txt'
    if config.is_file():
        value=config.read_text(encoding='utf-8').strip()
        if value and Path(value).is_absolute():return value
    return None

if __name__=='__main__':
    launch(sys.argv[1] if len(sys.argv)>1 else configured_workspace())
