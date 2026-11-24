"""Synthetic engineering tests only; no clinical performance claims."""
import csv
import json
from pathlib import Path
import numpy as np
import pytest
from vigil_studio.core.ecg_validation import (
    reference_beats, annotation_counts, pair_beats, evaluate_ecg_record,
    export_evaluation_csv, export_evaluation_json,
)
from vigil_studio.core.records import Record


def test_nonbeat_annotations_never_enter_beat_ground_truth():
    a = {'source':'atr','sample':[0,100,200,300,400],
         'symbol':['+','N','~','A','V']}
    assert reference_beats(a) == [
        {'sample':100,'symbol':'N'}, {'sample':300,'symbol':'A'}, {'sample':400,'symbol':'V'}]
    assert annotation_counts(a) == {'A':1,'N':1,'V':1}
    assert len(reference_beats(a, max_sample=350)) == 2


def test_rejects_non_atr_references():
    with pytest.raises(ValueError,match='original WFDB'):
        reference_beats({'source':'human_review','sample':[100],'symbol':['N']})
    with pytest.raises(ValueError,match='differ in length'):
        reference_beats({'source':'atr','sample':[100,200],'symbol':['N']})
    with pytest.raises(ValueError,match='ordered'):
        reference_beats({'source':'atr','sample':[200,100],'symbol':['N','N']})


def test_one_to_one_matching_and_timing_errors():
    r=pair_beats([100,200,300],[102,190,193,450],fs=100,tolerance_s=.15)
    m=r['metrics']
    assert (m['tp'],m['fp'],m['fn'])==(2,2,1)
    assert m['sensitivity']==pytest.approx(2/3, abs=1e-6)
    assert m['positive_predictive_value']==.5
    assert len(r['matches'])==2 and len(r['missed_reference_samples'])==1
    assert m['median_abs_timing_error_ms']==60.0
    assert m['p95_abs_timing_error_ms']==96.0


def test_zero_predictions_are_reported_as_missed_not_success():
    m=pair_beats([100,200,300],[],fs=250)['metrics']
    assert (m['tp'],m['fp'],m['fn'])==(0,0,3)
    assert m['sensitivity']==0
    assert m['positive_predictive_value'] is None
    assert m['f1']==0
    assert m['median_abs_timing_error_ms'] is None


def test_requires_non_duplicate_positions_and_valid_tolerance():
    with pytest.raises(ValueError,match='Duplicate'):
        pair_beats([1,1],[2],fs=200)
    with pytest.raises(ValueError,match='Tolerance'):
        pair_beats([1],[2],fs=200,tolerance_s=.7)


def make_test_record(fs=250,seconds=18):
    n=int(fs*seconds);t=np.arange(n)/fs
    x=np.zeros(n)
    positions=[int(v*fs) for v in range(1,seconds)]
    for pos in positions:
        x+=1.3*np.exp(-((np.arange(n)-pos)/(0.014*fs))**2)
    # A separate lead with a different amplitude, but identical timing.
    return Record({'MLII':x, 'V5':x*.45},fs,'SYNTHETIC_QRS_TEST','synthetic',
        'synthetic-sha256-not-actual-record',
        annotation={'source':'atr','sample':[0,*positions],
                    'symbol':['+', *(['N']*len(positions))],
                    'file_sha256':'synthetic-annotation-digest'})


def test_evaluation_only_uses_reference_during_comparison(monkeypatch, tmp_path):
    rec=make_test_record()
    captured=[]
    def fake_detector(data,fs,kind):
        captured.append((data.copy(),fs,kind))
        return np.array([250,500,750])
    monkeypatch.setattr('vigil_studio.core.ecg_validation.detect_peaks',fake_detector)
    report=evaluate_ecg_record(rec,'MLII',.15)
    assert len(captured)==1 and captured[0][1]==250
    assert captured[0][0].shape==rec.channels['MLII'].shape
    assert report['reference']['n_beat_annotations']==17
    assert report['detector']['n_predictions']==3
    assert report['reference']['location_detection_by_reference_symbol']['N']['detected_within_tolerance']==3
    assert report['detector']['uses_reference_labels_for_inference'] is False
    assert report['comparison']['metrics']['tp']==3
    assert report['comparison']['metrics']['fn']==14
    assert report['comparison']['metrics']['fp']==0
    jsonpath=export_evaluation_json(report,tmp_path/'report.json')
    csvpath=export_evaluation_csv(report,tmp_path/'events.csv')
    assert json.loads(jsonpath.read_text())['schema']=='vigil-ecg-reference-benchmark-1'
    with csvpath.open(newline='') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==17 and {r['event_type'] for r in rows}=={'TP','FN'}


def test_full_wfdb_record_import_and_atr_binding(monkeypatch,tmp_path):
    from vigil_studio.core.importers import read_wfdb
    import sys,types
    p=tmp_path/'100'
    p.with_suffix('.hea').write_text('mock hea',encoding='ascii')
    p.with_suffix('.dat').write_bytes(b'waveforms')
    p.with_suffix('.atr').write_bytes(b'marks')
    class Header:
        sig_len=18000
        fs=250
    class Signal:
        fs=250
        sig_name=['MLII','V5']
        p_signal=np.ones((18000,2))
    class Ann:
        sample=np.array([15,200,300])
        symbol=['+','N','V']
    called=[]
    def rdrecord(stem,sampfrom,sampto):
        called.append(sampto)
        return Signal()
    mock=types.SimpleNamespace(rdheader=lambda stem:Header(),rdrecord=rdrecord,
                               rdann=lambda stem,name,**kw:Ann() if name=='atr' else None)
    monkeypatch.setitem(sys.modules,'wfdb',mock)
    rec=read_wfdb(p.with_suffix('.hea'))
    assert called==[18000]   # Not silently truncated to 300 seconds.
    assert rec.n==18000 and rec.duration==72
    assert rec.annotation['symbol']==['+','N','V']
    assert len(rec.annotation['file_sha256'])==64
    assert len(rec.sha256)==64
    assert annotation_counts(rec.annotation)=={'N':1,'V':1}
