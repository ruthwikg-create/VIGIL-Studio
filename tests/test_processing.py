import numpy as np
import pytest
from vigil_studio.core.demo import make_demo
from vigil_studio.core.records import Record,record_to_npz,record_from_npz
from vigil_studio.core.processing import analyze_record,filter_trace,window_features,detect_peaks,hrv_features,normalized_type

@pytest.fixture(scope='module')
def demo():return make_demo(seconds=14)

def test_demo_is_labeled_and_multichannel(demo):
    assert demo.origin.startswith('SYNTHETIC')
    assert list(demo.channels)==['ECG','PPG','ABP','RESP']
    assert demo.n==3500

def test_analysis_produces_windows(demo):
    a=analyze_record(demo,window_s=4,stride_s=2)
    assert set(a['channels'])==set(demo.channels)
    assert a['channels']['ECG']['windows']
    assert a['engine'].startswith('vigil-signal')
    assert any('clinical' in x.lower() for x in a['limitations'])

def test_nan_gaps_stay_nan_after_filter():
    x=np.sin(np.linspace(0,30,1000));x[200:230]=np.nan
    y=filter_trace(x,125,'ecg')
    assert np.isnan(y[200:230]).all()
    assert np.isfinite(y[:200]).all()

def test_quality_detects_dropout():
    a=analyze_record(make_demo('dropout',seconds=15),window_s=3,stride_s=1.5)
    assert a['channels']['ECG']['missing_samples']>0
    assert a['channels']['ECG']['quality']['availability']<1

def test_record_npz_roundtrip(tmp_path,demo):
    path=tmp_path/'record.npz';record_to_npz(demo,path)
    out=record_from_npz(path)
    assert out.sha256==demo.sha256
    assert np.array_equal(out.channels['ECG'],demo.channels['ECG'])

def test_bad_record_length():
    with pytest.raises(ValueError):Record({'a':[1,2,3],'b':[1,2]},100,'x','s','')

def test_type_names():
    assert normalized_type('ECG II')=='ECG'
    assert normalized_type('PLETH')=='PPG'
    assert normalized_type('ART')=='ABP'
