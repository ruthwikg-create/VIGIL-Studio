import sys
from .ui.app import launch
if __name__=='__main__':
    launch(sys.argv[1] if len(sys.argv)>1 else None)
