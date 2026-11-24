from vigil_studio.core.store import Workspace
from vigil_studio.core.demo import make_demo
from vigil_studio.core.processing import analyze_record
from vigil_studio.core.modeling import load_labeled_segments,ExperimentError
import pytest

def test_manual_intervals_and_export(tmp_path):
    w=Workspace(tmp_path/'workspace')
    r=make_demo(seconds=20);a=analyze_record(r,window_s=4,stride_s=2)
    id=w.add_case(r,a)
    w.add_interval(id,'ECG',0,18,'subject_group_A','quality_acceptable',note='expert reviewed for research')
    assert len(w.intervals(id))==1
    summary=w.export_labeled_features(tmp_path/'labels.csv')
    assert summary['labeled_windows']>=5
    text=(tmp_path/'labels.csv').read_text()
    assert 'subject_group_A' in text
    assert 'quality_acceptable' in text
    assert w.verify_audit()['valid']

def test_conflicting_labels_not_used(tmp_path):
    w=Workspace(tmp_path/'w');r=make_demo(seconds=20);id=w.add_case(r,analyze_record(r))
    w.add_interval(id,'ECG',0,20,'subject1','quality_acceptable')
    w.add_interval(id,'ECG',0,20,'subject1','quality_unacceptable')
    result=w.export_labeled_features(tmp_path/'l.csv')
    assert result['labeled_windows']==0

def test_bad_interval_rejected(tmp_path):
    w=Workspace(tmp_path/'w');r=make_demo(seconds=20);id=w.add_case(r,analyze_record(r))
    with pytest.raises(ValueError):w.add_interval(id,'ECG',5,2,'group','quality_acceptable')
