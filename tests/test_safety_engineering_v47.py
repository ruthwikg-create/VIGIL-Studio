"""Threat-driven tests for optional research encryption and external audit anchors."""
import json
from pathlib import Path
import pytest
from vigil_studio.core.store import Workspace
from vigil_studio.core.demo import make_demo
from vigil_studio.core.processing import analyze_record
from vigil_studio.safety.encrypted_export import seal_bytes,unseal_bytes,seal_case,inspect_encrypted_case,MAGIC
from vigil_studio.safety.audit_anchor import create_key,create_anchor,verify_anchor
from vigil_studio.safety.gates import assess_release

STRONG='AnUnsharedLongPassphrase-2026!'


def test_auth_encryption_roundtrip_and_unique_nonce():
    raw=b'PUBLIC SYNTHETIC TEST ONLY' * 100
    blob=seal_bytes(raw,STRONG)
    assert blob.startswith(MAGIC)
    assert raw not in blob
    assert unseal_bytes(blob,STRONG)==raw
    assert seal_bytes(raw,STRONG)!=blob


def test_wrong_passphrase_and_modified_ciphertext_fail_closed():
    blob=seal_bytes(b'synthetic',STRONG)
    with pytest.raises(ValueError,match='Authentication failed'):
        unseal_bytes(blob,STRONG+'-wrong')
    for altered in [blob[:-1]+bytes([blob[-1]^1]),blob[:18]+bytes([blob[18]^1])+blob[19:],blob[:5],blob[:-19]]:
        with pytest.raises(ValueError):unseal_bytes(altered,STRONG)


def test_weak_passphrase_and_oversized_input_rejected():
    with pytest.raises(ValueError,match='14'):
        seal_bytes(b'payload','simple')
    with pytest.raises(ValueError,match='96'):
        seal_bytes(b'0'*(96*1024*1024+1),STRONG)


def _workspace(tmp_path):
    ws=Workspace(tmp_path/'workspace')
    rec=make_demo(seconds=12)
    key=ws.add_case(rec,analyze_record(rec))
    return ws,key


def test_saved_research_npz_roundtrip_without_plaintext_export(tmp_path):
    ws,key=_workspace(tmp_path)
    dest=tmp_path/'sealed'/'demo.ve1'
    seal_case(ws,key,dest,STRONG)
    raw=(ws.records/(key+'.npz')).read_bytes()
    assert raw!=dest.read_bytes()
    meta=inspect_encrypted_case(dest,STRONG)
    assert meta['envelope_authenticated']
    assert meta['samples_per_channel']>0
    assert meta['clinical_authorization'] is False
    assert not (dest.parent/'demo.npz').exists()
    with pytest.raises(FileExistsError):seal_case(ws,key,dest,STRONG)


def test_anchor_requires_external_key_and_external_file(tmp_path):
    ws,key=_workspace(tmp_path)
    with pytest.raises(ValueError,match='OUTSIDE'):
        create_key(ws.root,ws.root/'key.bin')
    external=tmp_path/'separate_device';external.mkdir()
    k=create_key(ws.root,external/'research_audit.key')
    a=create_anchor(ws,k,external/'snapshot_001.json')
    check=verify_anchor(ws,k,a)
    assert check['valid'] is True
    assert check['anchored_events']==1
    assert not (ws.root/'snapshot_001.json').exists()
    with pytest.raises(FileExistsError):create_anchor(ws,k,a)
    ws.add_review(key,'needs_review','synthetic note','test')
    assert verify_anchor(ws,k,a)['valid'] is True
    assert verify_anchor(ws,k,a)['new_events_since_anchor']==1


def test_anchor_detects_signature_tampering_and_history_rewrite(tmp_path):
    ws,key=_workspace(tmp_path)
    k=create_key(ws.root,tmp_path/'offline.key')
    a=create_anchor(ws,k,tmp_path/'baseline.json')
    with ws.conn() as c:c.execute("UPDATE audit SET kind='forged' WHERE seq=1")
    assert verify_anchor(ws,k,a)['valid'] is False
    # restore genuine audit and tamper signed checkpoint instead
    ws2,key2=_workspace(tmp_path/'new')
    k2=create_key(ws2.root,tmp_path/'offline2.key')
    a2=create_anchor(ws2,k2,tmp_path/'baseline2.json')
    data=json.loads(a2.read_text())
    data['claims']['event_count']=500
    a2.write_text(json.dumps(data))
    assert verify_anchor(ws2,k2,a2)['reason']=='anchor_authentication_failed'


def test_anchor_detects_audit_truncation(tmp_path):
    ws,key=_workspace(tmp_path)
    ws.add_review(key,'needs_review','note','test')
    k=create_key(ws.root,tmp_path/'separate.key')
    a=create_anchor(ws,k,tmp_path/'sealed.json')
    with ws.conn() as c:c.execute('DELETE FROM audit WHERE seq=2')
    check=verify_anchor(ws,k,a)
    assert not check['valid'] and check['reason']=='audit_truncated'


def test_readiness_stays_blocked_after_security_controls(tmp_path):
    ws,key=_workspace(tmp_path)
    k=create_key(ws.root,tmp_path/'external.key')
    a=create_anchor(ws,k,tmp_path/'checkpoint.json')
    r=assess_release(ws)
    assert r['clinical_release_decision']=='BLOCKED'
    assert all(g['state']=='BLOCKED' for g in r['clinical_gates'])


def test_legacy_unverified_record_cannot_be_sealed(tmp_path):
    ws,key=_workspace(tmp_path)
    with ws.conn() as c: c.execute('UPDATE cases SET artifact_sha256=NULL WHERE id=?',(key,))
    with pytest.raises(ValueError,match='unverified legacy'):
        seal_case(ws,key,tmp_path/'no.ve1',STRONG)

def test_release_security_status_can_verify_external_anchor(tmp_path):
    ws,key=_workspace(tmp_path)
    k=create_key(ws.root,tmp_path/'audit.key')
    a=create_anchor(ws,k,tmp_path/'audit.json')
    status=assess_release(ws,audit_key_path=k,audit_anchor_path=a)
    assert status['security_controls']['external_audit_anchor']['status']=='VERIFIED_LOCAL_ANCHOR'
    assert status['security_controls']['existing_workspace_encrypted_at_rest'] is False
    assert status['clinical_release_decision']=='BLOCKED'
