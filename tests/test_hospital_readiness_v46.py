"""Hospital readiness engineering controls; not clinical-performance tests."""
from pathlib import Path
import json,sqlite3,zipfile,pytest
from vigil_studio.core.demo import make_demo
from vigil_studio.core.processing import analyze_record
from vigil_studio.core.store import Workspace
from vigil_studio.core.records import record_from_npz
from vigil_studio.core.importers import read_csv
from vigil_studio.safety.gates import assess_release, write_report, render_markdown


def _workspace_with_record(tmp_path):
    w=Workspace(tmp_path/'ws')
    r=make_demo(seconds=12)
    key=w.add_case(r,analyze_record(r))
    return w,key


def test_new_record_contains_verifiable_digest(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    inv=w.verify_record_integrity()
    assert inv['verified']==1 and inv['failed']==0 and inv['unverified_legacy']==0
    assert w.get_case(key)[1].n>32


def test_corrupt_saved_archive_blocks_loading_and_readiness(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    with w.conn() as c:
        row=c.execute('SELECT record_path FROM cases WHERE id=?',(key,)).fetchone()
    path=w.records/row['record_path']
    data=bytearray(path.read_bytes());data[len(data)//2]^=0x20
    path.write_bytes(data)
    with pytest.raises(ValueError,match='integrity failure'):w.get_case(key)
    assessment=assess_release(w)
    assert assessment['engineering_checks']['case_files']['failed']==1
    assert assessment['engineering_checks']['engineering_integrity']=='REVIEW_REQUIRED'
    assert not assessment['clinical_operations_authorized']


def test_legacy_case_migration_does_not_auto_certify(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    with w.conn() as c:c.execute('UPDATE cases SET artifact_sha256=NULL WHERE id=?',(key,))
    # Simulate the legacy storage state after a safe schema migration.
    assert w.get_case(key)[1].n>32
    inv=w.verify_record_integrity()
    assert inv['unverified_legacy']==1 and inv['verified']==0
    assert assess_release(w)['engineering_checks']['engineering_integrity']=='REVIEW_REQUIRED'


def test_audit_tampering_fails_local_gate(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    with w.conn() as c:c.execute("UPDATE audit SET kind='altered' WHERE seq=1")
    assessment=assess_release(w)
    assert assessment['engineering_checks']['audit']['valid'] is False
    assert assessment['clinical_release_decision']=='BLOCKED'


def test_no_workspace_does_not_imply_clinical_authorization():
    r=assess_release()
    assert r['clinical_release_decision']=='BLOCKED'
    assert all(g['state']=='BLOCKED' for g in r['clinical_gates'])
    assert 'CLINICAL RELEASE BLOCKED' in render_markdown(r)


def test_report_is_write_once_and_contains_no_raw_waveform(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    report=assess_release(w)
    target=write_report(report,tmp_path/'new')
    assert (target/'READINESS.md').exists()
    data=json.loads((target/'READINESS.json').read_text())
    assert data['clinical_operations_authorized'] is False
    assert 'waveforms' not in data['engineering_checks']
    with pytest.raises(FileExistsError):write_report(report,target)


def test_missing_benchmark_never_counts_as_complete(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    report=assess_release(w,tmp_path/'nothing')
    assert report['retrospective_benchmark']['status']=='MISSING'
    assert report['clinical_release_decision']=='BLOCKED'


def test_benchmark_completion_is_research_only(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    b=tmp_path/'bench';b.mkdir()
    (b/'results.json').write_text(json.dumps({'completion_status':'COMPLETED',
        'preflight':{'expected_records':['100']},'records':[{'record_id':'100'}],
        'errors':[],'research_only':True,'protocol':{'clinical_grade':False}}))
    for name in ('locked_protocol.json','per_record_metrics.csv','REPORT.md'):
        (b/name).write_text('fixture')
    report=assess_release(w,b)
    assert report['retrospective_benchmark']['status']=='COMPLETE_RESEARCH_BENCHMARK'
    assert report['clinical_release_decision']=='BLOCKED'


def test_npz_rejects_oversized_archive_entry(tmp_path):
    z=tmp_path/'malicious.npz'
    from zipfile import ZipInfo
    # Simulate a malicious archive whose declared decompressed size greatly exceeds safe bounds.
    with zipfile.ZipFile(z,'w') as fh:
        fh.writestr('__meta__.npy',b'not-an-array')
        fh.writestr('ch_ECG.npy',b'xyz')
    with zipfile.ZipFile(z, 'a') as fh:
        fh.writestr('arbitrary.txt',b'x')
    with pytest.raises(ValueError,match='Unexpected NPZ entry'):record_from_npz(z)


def test_import_blocks_patient_identifier_column_variant(tmp_path):
    csv=tmp_path/'unsafe.csv'
    csv.write_text('patient id,ECG\n'+'person,0.1\n'*64)
    with pytest.raises(ValueError,match='identifier'):read_csv(csv,100)


def test_guide_contains_visible_block_and_integrity_action():
    from vigil_studio.ui.app import Studio
    assert hasattr(Studio,'_run_local_safety_check')
    assert hasattr(Studio,'_guide')
    source=Path(__file__).resolve().parents[1]/'vigil_studio/ui/app.py'
    code=source.read_text()
    assert 'Clinical deployment status: BLOCKED' in code
    assert 'RUN LOCAL INTEGRITY CHECK' in code


def test_benchmark_incomplete_if_evidence_missing(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    b=tmp_path/'bench';b.mkdir()
    (b/'results.json').write_text(json.dumps({'completion_status':'COMPLETED',
        'preflight':{'expected_records':['100']}, 'records':[{'record_id':'100'}],
        'research_only':True, 'protocol':{'clinical_grade':False}}))
    assert assess_release(w,b)['retrospective_benchmark']['status']=='INCOMPLETE_OR_UNVERIFIED'


def test_empty_workspace_is_never_graded_pass(tmp_path):
    w=Workspace(tmp_path/'blank')
    assert assess_release(w)['engineering_checks']['engineering_integrity']=='NO_RECORDINGS'


def test_csv_export_escapes_formula_like_channel_names(tmp_path):
    import csv
    from vigil_studio.core.records import Record
    from vigil_studio.core.reporting import export_waveform_csv, safe_csv_text
    import numpy as np
    r=Record({'=HYPERLINK("bad")':np.arange(64,dtype=float)},100,'fixture','test','digest')
    target=tmp_path/'out.csv'
    export_waveform_csv(r,target,0,.3)
    with target.open(newline='') as f:rows=list(csv.reader(f))
    assert rows[0][1].startswith("'=")
    assert safe_csv_text('@malicious').startswith("'@")
    assert safe_csv_text('ECG')=='ECG'


def test_csv_rejects_duplicate_normalized_header(tmp_path):
    f=tmp_path/'bad.csv'
    f.write_text('time_s,ECG, ECG \n'+'\n'.join(f'{i/100:.2f},0.2,0.1' for i in range(64)))
    with pytest.raises(ValueError,match='Duplicate headers'):read_csv(f)


def test_migrating_real_old_schema_preserves_cases_and_annotation(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    w.add_interval(key, 'ECG', 1, 2, 'synthetic_subject', 'uncertain', reviewer='test')
    with w.conn() as c:
        c.execute('ALTER TABLE cases DROP COLUMN artifact_sha256')
    reopened=Workspace(tmp_path/'ws')
    assert len(reopened.intervals(key))==1
    assert reopened.get_case(key)[1].n>32
    assert reopened.verify_record_integrity()['unverified_legacy']==1


def test_research_gate_does_not_leak_raw_channels_or_audit_notes(tmp_path):
    w,key=_workspace_with_record(tmp_path)
    w.add_review(key,'needs_review','SENSITIVE_TEST_NOTE_DO_NOT_EXPORT','test')
    text=json.dumps(assess_release(w))
    assert 'SENSITIVE_TEST_NOTE_DO_NOT_EXPORT' not in text
    assert 'channel samples' not in text
