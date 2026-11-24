"""Offline research-safety CLI. No clinical or patient-care mode is available."""
from __future__ import annotations
import argparse,getpass,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from vigil_studio.core.store import Workspace
from vigil_studio.safety.encrypted_export import seal_case,inspect_encrypted_case
from vigil_studio.safety.audit_anchor import create_key,create_anchor,verify_anchor


def main(argv=None):
    p=argparse.ArgumentParser(description='VIGIL research encryption / external audit verification, NOT a hospital security system')
    p.add_argument('--workspace',default=str(Path.home()/'VIGILStudio_Workspace'))
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('list-case-ids',help='Show local research case identifiers without waveform values')
    enc=sub.add_parser('encrypt-case');enc.add_argument('--case-id',required=True);enc.add_argument('--output',required=True)
    inspect=sub.add_parser('inspect-encrypted');inspect.add_argument('--file',required=True)
    key=sub.add_parser('create-audit-key');key.add_argument('--key-path',required=True)
    seal=sub.add_parser('seal-audit');seal.add_argument('--key-path',required=True);seal.add_argument('--output',required=True)
    check=sub.add_parser('verify-audit');check.add_argument('--key-path',required=True);check.add_argument('--anchor',required=True)
    a=p.parse_args(argv)
    ws=Workspace(a.workspace)
    if a.command=='list-case-ids':
        for case in ws.list_cases():
            print(case['id'],case['created'][:19],case['origin'])
    elif a.command=='encrypt-case':
        pw=getpass.getpass('Research export passphrase (14+ chars): ')
        if pw!=getpass.getpass('Confirm passphrase: '): raise ValueError('Passphrases did not match')
        print('Encrypted research handoff:',seal_case(ws,a.case_id,Path(a.output),pw))
    elif a.command=='inspect-encrypted':
        pw=getpass.getpass('Research export passphrase: ')
        print(json.dumps(inspect_encrypted_case(Path(a.file),pw),indent=2))
    elif a.command=='create-audit-key':
        print('External key saved. Store securely outside project and workspace:',create_key(ws.root,Path(a.key_path)))
    elif a.command=='seal-audit':
        print('Read-only audit prefix anchored:',create_anchor(ws,Path(a.key_path),Path(a.output)))
    elif a.command=='verify-audit':
        status=verify_anchor(ws,Path(a.key_path),Path(a.anchor))
        print(json.dumps(status,indent=2))
        if not status['valid']:return 2
    print('RESEARCH ONLY. These tools do not enable patient-care or clinical mode.')
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as e:
        print(f'BLOCKED: {e}',file=sys.stderr);raise SystemExit(2)
