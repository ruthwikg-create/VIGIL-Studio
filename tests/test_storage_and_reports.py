import json,sqlite3
from vigil_studio.core.demo import make_demo
from vigil_studio.core.processing import analyze_record
from vigil_studio.core.store import Workspace
from vigil_studio.core.reporting import export_window_csv,pdf_report,export_waveform_csv

def test_case_review_and_audit(tmp_path):
    w=Workspace(tmp_path/'store');r=make_demo(seconds=12);a=analyze_record(r)
    id=w.add_case(r,a);assert len(w.list_cases())==1
    row,loaded,loaded_a=w.get_case(id)
    assert loaded.n==r.n
    assert loaded_a['record']['sha256']==r.sha256
    w.add_review(id,'needs_review','Review test','user')
    assert len(w.reviews(id))==1
    assert w.verify_audit()['valid']
    out=tmp_path/'case.json';w.export_case_json(id,out)
    result=json.loads(out.read_text());assert result['raw_waveforms_not_embedded']

def test_audit_tampering_detected(tmp_path):
    w=Workspace(tmp_path/'store');r=make_demo(seconds=12);id=w.add_case(r,analyze_record(r))
    with w.conn() as c:c.execute("UPDATE audit SET subject='changed' WHERE seq=1")
    assert not w.verify_audit()['valid']

def test_csv_and_pdf_exports(tmp_path):
    r=make_demo(seconds=12);a=analyze_record(r,window_s=3,stride_s=1)
    export_window_csv(a,tmp_path/'windows.csv')
    assert 'quality_score' in (tmp_path/'windows.csv').read_text()
    export_waveform_csv(r,tmp_path/'wave.csv',1,2)
    assert len((tmp_path/'wave.csv').read_text().splitlines())==501
    path=pdf_report(r,a,[],tmp_path/'report.pdf')
    assert path.read_bytes()[:4]==b'%PDF'
    assert path.stat().st_size>1500
