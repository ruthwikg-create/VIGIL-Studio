"""Operator-controlled external authentication for VIGIL's existing audit log.

HMAC anchors detect tampering/truncation relative to a snapshot retained OUTSIDE
of the workspace. A malicious operator who can modify both the separate key and
anchor can defeat these controls. They are not WORM or independent SIEM logs.
"""
from __future__ import annotations
import hashlib,hmac,json,os,secrets
from pathlib import Path
from datetime import datetime,timezone


def _outside(root, candidate):
    root=Path(root).expanduser().resolve();path=Path(candidate).expanduser().resolve()
    if path==root or root in path.parents:
        raise ValueError('Audit key and anchors must live OUTSIDE the writable workspace')
    return path


def create_key(workspace_root:Path,output:Path):
    path=_outside(workspace_root,output)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(secrets.token_bytes(32));stream.flush();os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True);raise
    return path


def _read_key(path):
    key=Path(path).read_bytes()
    if len(key)!=32:raise ValueError('Invalid external audit-authentication key')
    return key


def create_anchor(ws,key_path:Path,anchor_path:Path):
    _outside(ws.root,key_path)
    target=_outside(ws.root,anchor_path)
    audit=ws.verify_audit()
    if not audit['valid']: raise ValueError('Cannot seal invalid audit chain')
    if audit['events_checked']==0:raise ValueError('No events to anchor')
    claims={'schema':'vigil-audit-hmac-anchor-v1','event_count':audit['events_checked'],
            'head_hash':audit['head_hash'],'created_utc':datetime.now(timezone.utc).isoformat()}
    canonical=json.dumps(claims,sort_keys=True,separators=(',',':')).encode()
    signature=hmac.new(_read_key(key_path),canonical,'sha256').hexdigest()
    payload=json.dumps({'claims':claims,'hmac_sha256':signature},indent=2).encode()+b'\n'
    target.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(payload);f.flush();os.fsync(f.fileno())
    except BaseException:
        target.unlink(missing_ok=True);raise
    return target


def verify_anchor(ws,key_path:Path,anchor_path:Path):
    _outside(ws.root,key_path);_outside(ws.root,anchor_path)
    try:
        envelope=json.loads(Path(anchor_path).read_text('utf8'))
        claims=envelope['claims']
        if claims['schema']!='vigil-audit-hmac-anchor-v1' or not isinstance(claims['event_count'],int) or claims['event_count']<1:
            raise ValueError('Invalid claims')
        expected=hmac.new(_read_key(key_path),json.dumps(claims,sort_keys=True,separators=(',',':')).encode(),'sha256').hexdigest()
        if not hmac.compare_digest(expected,envelope['hmac_sha256']):
            return {'valid':False,'reason':'anchor_authentication_failed'}
        rows=ws.audit()
        if len(rows)<claims['event_count']:
            return {'valid':False,'reason':'audit_truncated'}
        if not ws.verify_audit()['valid']:
            return {'valid':False,'reason':'audit_chain_modified'}
        if not hmac.compare_digest(rows[claims['event_count']-1]['hash'],claims['head_hash']):
            return {'valid':False,'reason':'audit_history_does_not_match_sealed_anchor'}
        return {'valid':True,'anchored_events':claims['event_count'],
                'new_events_since_anchor':len(rows)-claims['event_count'],
                'scope':'External HMAC attestation of local research audit prefix, not tamper-proof logging'}
    except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError):
        return {'valid':False,'reason':'invalid_or_unreadable_anchor'}
