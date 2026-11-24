"""Read-only assessment: never sends records or changes care actions."""
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from vigil_studio.core.store import Workspace
from vigil_studio.safety.gates import assess_release,write_report

def main(argv=None):
    p=argparse.ArgumentParser(description='Offline research integrity and hospital readiness gate (NEVER clinical authorization)')
    p.add_argument('--workspace',default=str(Path.home()/'VIGILStudio_Workspace'))
    p.add_argument('--benchmark-dir',default=None)
    p.add_argument('--output',required=True,help='NEW results folder; existing results are never overwritten')
    p.add_argument('--audit-anchor',default=None,help='Optional external audit seal JSON')
    p.add_argument('--audit-key',default=None,help='External 32-byte HMAC key, not in workspace')
    a=p.parse_args(argv)
    assessment=assess_release(Workspace(Path(a.workspace)), a.benchmark_dir, audit_anchor_path=a.audit_anchor, audit_key_path=a.audit_key)
    dest=write_report(assessment,Path(a.output))
    print('Engineering assessment saved:',dest)
    print('CLINICAL RELEASE BLOCKED — evidence package is research only')
    return 0 if assessment['engineering_checks']['engineering_integrity']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
