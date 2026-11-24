import csv,json
import numpy as np
import pytest
from vigil_studio.core.modeling import train_experiment,predict_quality,save_model,ExperimentError,FEATURE_FIELDS

def create_labeled(path,n_groups=10,n_per=12):
    rng=np.random.default_rng(10)
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['group_id','label',*FEATURE_FIELDS]);w.writeheader()
        for g in range(n_groups):
            for i in range(n_per):
                cls=(i+g)%2
                features={k:float(rng.normal(loc=cls*1.0,scale=.35)) for k in FEATURE_FIELDS}
                w.writerow({'group_id':f'record_{g:02d}','label':'quality_acceptable' if cls else 'quality_unacceptable',**features})

def test_group_holdout_model_serialization(tmp_path):
    p=tmp_path/'labels.csv';create_labeled(p)
    result,model=train_experiment(p)
    assert result['group_overlap']==0
    assert result['n_holdout_groups']>=1
    assert 0<=result['roc_auc']<=1
    out=tmp_path/'model.json';save_model(model,out)
    loaded=json.loads(out.read_text())
    example={k:1.3 for k in FEATURE_FIELDS};pred=predict_quality(example,loaded)
    assert pred['category'] in {'ABSTAIN_UNCERTAIN','RESEARCH_QUALITY_ACCEPTABLE','RESEARCH_QUALITY_UNACCEPTABLE'}

def test_incomplete_labels_rejected(tmp_path):
    p=tmp_path/'bad.csv';p.write_text('group_id,label\nrec,quality_acceptable\n')
    with pytest.raises(ExperimentError):train_experiment(p)

def test_model_rejects_corrupted_schema():
    with pytest.raises(ExperimentError):predict_quality({k:1. for k in FEATURE_FIELDS},{'schema':'wrong'})
