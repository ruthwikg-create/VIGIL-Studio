"""Verify a VIGIL controlled research evidence ZIP without unpacking its files."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from vigil_studio.core.evidence_bundle import verify_evidence_package

def main(argv=None):
    p=argparse.ArgumentParser(description='Read-only integrity verifier, NOT a clinical release decision')
    p.add_argument('zip_file',type=Path)
    a=p.parse_args(argv)
    try:
        result=verify_evidence_package(a.zip_file)
        print(f"PASS - verified {result['files_checked']} evidence files for {result['record_name']}")
        print(result['note'])
        return 0
    except Exception as exc:
        print(f"FAIL - {type(exc).__name__}: {exc}",file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
