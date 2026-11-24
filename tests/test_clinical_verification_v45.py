import json
from pathlib import Path
import pytest
from scripts import clinical_readiness_benchmark as bench


def test_expected_record_count():
    assert len(bench.EXPECTED)==48
    assert len(set(bench.EXPECTED))==48
    assert '100' in bench.EXPECTED and '234' in bench.EXPECTED


def test_preflight_does_not_treat_annotation_only_as_complete(tmp_path):
    for suffix in ('.hea','.dat'):
        (tmp_path/('100'+suffix)).write_bytes(b'abc')
    p=bench.preflight(tmp_path,('100',))
    assert p['complete_records']==[]
    assert p['missing'][0]['missing_files']==['100.atr']


def test_preflight_rejects_empty_file(tmp_path):
    for suffix in ('.hea','.dat','.atr'):
        (tmp_path/('100'+suffix)).write_bytes(b'data')
    (tmp_path/'100.atr').write_bytes(b'')
    p=bench.preflight(tmp_path,('100',))
    assert p['complete_records']==[]
    assert p['empty'][0]['empty_files']==['100.atr']


def test_discover_nested_dataset(tmp_path):
    (tmp_path/'dataset').mkdir()
    (tmp_path/'dataset'/'100.hea').touch()
    assert bench.discover_root(tmp_path) == tmp_path/'dataset'


def test_no_posthoc_tolerance_change():
    assert bench.TOLERANCE_SECONDS==.150
    assert 'fixed' in bench.PROTOCOL_ID


def test_pooled_metrics_are_count_based():
    a={'tp':5,'fp':1,'fn':5,'sensitivity':.5,'positive_predictive_value':5/6,'f1':.625,'per_reference_symbol':{'N':{'reference':10,'detected_within_tolerance':5,'missed':5}}}
    b={'tp':10,'fp':2,'fn':0,'sensitivity':1,'positive_predictive_value':10/12,'f1':20/22,'per_reference_symbol':{'N':{'reference':10,'detected_within_tolerance':10,'missed':0}}}
    s=bench.aggregate([a,b])
    assert s['pooled']['tp']==15
    assert s['pooled']['fp']==3
    assert s['pooled']['fn']==5
    assert s['pooled']['sensitivity']==.75
    assert s['per_reference_symbol_location_matches']['N']['missed']==5


def test_bootstrap_reproducible_on_record_level():
    rows=[{'tp':20,'fp':2,'fn':3},{'tp':4,'fp':5,'fn':12},{'tp':50,'fp':0,'fn':1}]
    assert bench.record_bootstrap(rows,n=100,seed=42)==bench.record_bootstrap(rows,n=100,seed=42)
    assert bench.record_bootstrap(rows[:1])=={}


def test_single_record_smoke_runs_with_injected_reader(tmp_path, monkeypatch):
    for suffix in ('.hea','.dat','.atr'):
        (tmp_path/('100'+suffix)).write_bytes(b'data')
    class FakeRec:
        name='100'
        fs=360
        duration=1805.55
        channels={'MLII':[0]*100}
        annotation={'source':'atr','sample':[5,50], 'symbol':['N','A'],'file_sha256':'abc'}
        sha256='fake-fixture'
    monkeypatch.setattr(bench,'read_wfdb',lambda _: FakeRec())
    def fake_eval(rec,lead,tolerance):
        assert lead == 'MLII' and tolerance == .15
        return {
            'schema': 'vigil-ecg-reference-benchmark-1', 'fs_hz': 360,
            'reference': {
                'n_beat_annotations': 2,
                'location_detection_by_reference_symbol': {
                    'N': {'reference': 1, 'detected_within_tolerance': 1, 'missed': 0},
                    'A': {'reference': 1, 'detected_within_tolerance': 0, 'missed': 1},
                },
            },
            'detector': {'n_predictions': 2},
            'comparison': {
                'metrics': {'tp': 1, 'fp': 1, 'fn': 1,
                            'sensitivity': .5, 'positive_predictive_value': .5, 'f1': .5,
                            'median_abs_timing_error_ms': 12, 'p95_abs_timing_error_ms': 12},
                'matches': [{'reference_sample': 5, 'predicted_sample': 9,
                             'signed_error_ms': 11.11}],
                'missed_reference_samples': [50],
                'unmatched_prediction_samples': [80],
            },
        }
    monkeypatch.setattr(bench,'evaluate_ecg_record',fake_eval)
    out=tmp_path/'results'
    result,code=bench.execute(tmp_path,out,('100',))
    assert code==0 and result['completion_status']=='COMPLETED'
    assert result['summary']['pooled']['tp']==1
    assert (out/'REPORT.md').exists()
    assert (out/'per_record_metrics.csv').exists()
    assert json.loads((out/'locked_protocol.json').read_text())['clinical_grade'] is False
    assert 'NOT MEDICALLY CERTIFIED' in (out/'REPORT.md').read_text()
    with pytest.raises(ValueError,match='already exists'):
        bench.execute(tmp_path,out,('100',))


def test_incomplete_runs_fail_gate(tmp_path,monkeypatch):
    (tmp_path/'100.hea').write_bytes(b'x')
    out=tmp_path/'results'
    run,code=bench.execute(tmp_path,out,('100',))
    assert code==2 and run['completion_status']=='INCOMPLETE'
    assert run['summary']['pooled']['sensitivity'] is None


def test_no_false_clinical_labels_in_report():
    r={'records':[],'preflight':{'expected_records':['100'],'missing':[],'empty':[]},'errors':[],'summary':{'pooled':{'tp':None}}}
    text=bench.make_report(r)
    assert 'NOT MEDICALLY CERTIFIED' in text
    assert 'not arrhythmia diagnosis' in text.lower() or 'not arrhythmia' in text.lower()
