"""Research-only ML experiment: safe JSON weights, group-separated held-out evaluation."""
from __future__ import annotations
from pathlib import Path
import csv,hashlib,json,math
import numpy as np
from .processing import FEATURE_FIELDS

MODEL_SCHEMA='vigil-quality-linear-1'

class ExperimentError(ValueError):pass

def load_labeled_segments(path):
    """CSV columns: group_id,label + FEATURE_FIELDS. group_id must identify subject/recording.
    Labels: quality_acceptable=1; quality_unacceptable=0. No patient IDs in file.
    """
    path=Path(path);raw=path.read_bytes()
    if len(raw)>100*1024*1024:raise ExperimentError('Labels CSV exceeds 100 MB')
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        expected={'group_id','label',*FEATURE_FIELDS}
        if not expected.issubset(reader.fieldnames or []):
            raise ExperimentError('Missing required feature, group_id or label column')
        features=[];labels=[];groups=[]
        for i,row in enumerate(reader,2):
            label=row['label'].strip()
            if label not in ('quality_acceptable','quality_unacceptable'):raise ExperimentError(f'Invalid label row {i}')
            group=row['group_id'].strip()
            if not group or len(group)>128:raise ExperimentError(f'Invalid group_id row {i}')
            try:values=[float(row[k]) for k in FEATURE_FIELDS]
            except (TypeError,ValueError) as exc:raise ExperimentError(f'Invalid feature row {i}') from exc
            if not all(math.isfinite(v) for v in values):raise ExperimentError(f'Nonfinite feature row {i}')
            features.append(values);labels.append(1 if label=='quality_acceptable' else 0);groups.append(group)
    if len(labels)<30 or len(set(groups))<6 or len(set(labels))<2:
        raise ExperimentError('Need >=30 independently labelled segments, >=6 recording groups, both classes')
    return np.asarray(features),np.asarray(labels),np.asarray(groups),hashlib.sha256(raw).hexdigest()

def train_experiment(labeled_csv,seed=42,holdout_fraction=0.25):
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import confusion_matrix,roc_auc_score,balanced_accuracy_score,brier_score_loss
    X,y,groups,digest=load_labeled_segments(labeled_csv)
    spl=GroupShuffleSplit(n_splits=1,test_size=holdout_fraction,random_state=seed)
    idx_train,idx_test=next(spl.split(X,y,groups))
    if len(np.unique(y[idx_train]))<2 or len(np.unique(y[idx_test]))<2:
        raise ExperimentError('Held-out grouping lacks both classes; add diverse independent recordings')
    scaler=StandardScaler();xt=scaler.fit_transform(X[idx_train]);xv=scaler.transform(X[idx_test])
    clf=LogisticRegression(class_weight='balanced',random_state=seed,max_iter=1000)
    clf.fit(xt,y[idx_train]);p=clf.predict_proba(xv)[:,1]
    # Abstention is a *research reporting category*; not a patient-safety guarantee.
    abstain=np.abs(p-0.5)<0.15
    predictions=(p>=.5).astype(int)
    conf=confusion_matrix(y[idx_test],predictions,labels=[0,1]).tolist()
    result={'kind':'OFFLINE_RESEARCH_ONLY','n_total':int(len(y)),
            'n_train':int(len(idx_train)),'n_holdout':int(len(idx_test)),
            'n_train_groups':int(len(set(groups[idx_train]))),'n_holdout_groups':int(len(set(groups[idx_test]))),
            'group_overlap':int(len(set(groups[idx_train]).intersection(groups[idx_test]))),
            'class_count_train':np.bincount(y[idx_train],minlength=2).tolist(),
            'class_count_holdout':np.bincount(y[idx_test],minlength=2).tolist(),
            'confusion_matrix_rows_actual_0_1':conf,
            'balanced_accuracy':round(float(balanced_accuracy_score(y[idx_test],predictions)),5),
            'roc_auc':round(float(roc_auc_score(y[idx_test],p)),5),
            'brier_score':round(float(brier_score_loss(y[idx_test],p)),5),
            'abstention_fraction':round(float(np.mean(abstain)),5),
            'dataset_sha256':digest,'split_seed':seed,
            'limitations':['Exploratory quality classification; not event detection or diagnosis',
                'Single held-out group split; external validation and label adjudication still necessary',
                'Metrics are not clinical sensitivity/specificity or trial results']}
    model={'schema':MODEL_SCHEMA,'feature_fields':FEATURE_FIELDS,
           'coef':clf.coef_[0].astype(float).tolist(),
           'intercept':float(clf.intercept_[0]),
           'mean':scaler.mean_.astype(float).tolist(),
           'scale':scaler.scale_.astype(float).tolist(),
           'train_dataset_sha256':digest,'split_seed':seed,
           'intended_use':'OFFLINE_EXPLORATORY_SIGNAL_QUALITY_RESEARCH_ONLY'}
    return result,model

def save_model(model,path):
    validate_model(model)
    Path(path).write_text(json.dumps(model,indent=2,allow_nan=False),encoding='utf-8')

def validate_model(model):
    if model.get('schema')!=MODEL_SCHEMA or model.get('feature_fields')!=FEATURE_FIELDS:
        raise ExperimentError('Unsupported model schema')
    n=len(FEATURE_FIELDS)
    for key in ('coef','mean','scale'):
        vals=model.get(key,[])
        if len(vals)!=n or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in vals):
            raise ExperimentError('Invalid model '+key)
    if any(v<=0 for v in model['scale']) or not math.isfinite(model.get('intercept',float('nan'))):
        raise ExperimentError('Invalid model scale or intercept')

def predict_quality(features,model,abstain_margin=.15):
    """Generic offline quality flag; NEVER a clinically actionable decision."""
    validate_model(model)
    x=np.asarray([float(features[k]) for k in FEATURE_FIELDS])
    if not np.all(np.isfinite(x)):return {'category':'ABSTAIN_NONFINITE','score':None}
    z=float(np.dot((x-np.asarray(model['mean']))/np.asarray(model['scale']),model['coef'])+model['intercept'])
    p=float(1/(1+np.exp(-np.clip(z,-60,60))))
    return {'category':'ABSTAIN_UNCERTAIN' if abs(p-0.5)<abstain_margin else
            ('RESEARCH_QUALITY_ACCEPTABLE' if p>=.5 else 'RESEARCH_QUALITY_UNACCEPTABLE'),
            'score':round(p,5),'not_calibrated_probability':True}
