import csv,json,os
from pathlib import Path
import numpy as np
import pytest
from scripts.make_synthetic_ai_fixture import create
from vigil_studio.ai.datasets import load_manifest,load_cohort,split_by_group,DatasetError,extract_window
from vigil_studio.ai.registry import model_status,RegistryError,install_moment
from vigil_studio.ai.experiment import train_model,TrainConfig,load_trained_model,predict_waveform_quality
from vigil_studio.core.importers import open_record

def test_cohort_manifest_and_provenance(tmp_path):
    m=create(tmp_path/'cohort')
    rows,digest=load_manifest(m)
    assert len(rows)==48
    assert all(r.modality=='ECG' for r in rows)
    c=load_cohort(m)
    assert c.x.shape==(48,512) and np.isfinite(c.x).all()
    a,b,t=split_by_group(c.y,c.groups)
    assert not (set(c.groups[a])&set(c.groups[b]))
    assert not (set(c.groups[a])&set(c.groups[t]))
    assert not (set(c.groups[b])&set(c.groups[t]))
    assert all(set(c.y[i])=={0,1} for i in (a,b,t))

def test_reject_traversal_group_leakage(tmp_path):
    m=create(tmp_path/'cohort')
    content=m.read_text()
    m.write_text(content.replace('synthetic_group_00.npz','../synthetic_group_00.npz'))
    with pytest.raises(DatasetError,match='paths'):load_manifest(m)
    m=create(tmp_path/'cohort')
    content=m.read_text()
    m.write_text(content.replace('SYNTH_00,1,ECG','SYNTH_BAD,1,ECG',1))
    with pytest.raises(DatasetError,match='multiple group'):load_manifest(m)

def test_model_manager_requires_consent_and_actual_weights(tmp_path):
    status=model_status(tmp_path)
    assert not status['installed'] and status['status']=='NOT_INSTALLED'
    with pytest.raises(RegistryError,match='License'):install_moment(tmp_path,False)

def test_real_torch_training_and_integrity(tmp_path):
    m=create(tmp_path/'cohort')
    out=tmp_path/'run_001'
    report=train_model(m,out,TrainConfig(epochs=2,batch_size=16,width=8,patience=2,device='cpu',seed=71))
    assert (out/'model.safetensors').is_file()
    assert report['group_overlap']==0
    assert report['test_windows']>0 and report['validation_windows']>0
    assert report['test_metrics']['roc_auc'] is not None
    assert (out/'split_assignments.csv').is_file()
    model,card=load_trained_model(out)
    record=open_record(tmp_path/'cohort'/'synthetic_group_00.npz')
    result=predict_waveform_quality(record,'ECG',out)
    assert 0<=result['quality_acceptable_score']<=1
    assert 'RESEARCH' in result['model_label']
    with pytest.raises(ValueError,match='empty'):train_model(m,out,TrainConfig(epochs=1,width=8))
    with (out/'model.safetensors').open('ab') as f:f.write(b'changed')
    with pytest.raises(ValueError,match='integrity'):load_trained_model(out)
