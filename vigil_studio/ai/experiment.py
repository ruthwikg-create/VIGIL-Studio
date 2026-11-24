"""Reproducible, group-disjoint offline waveform research training.

NO CLINICAL MODEL CLAIMS. All labels must be independently collected.
The test split is held out until training and selection finish.
"""
from __future__ import annotations
import csv, datetime, hashlib, json, os, random, time
from pathlib import Path
from dataclasses import dataclass, asdict
import numpy as np
from .datasets import load_cohort,split_by_group,extract_window,DatasetError
from .network import build_network

SCHEMA='vigil-torch-quality-v2'

@dataclass(frozen=True)
class TrainConfig:
    epochs:int=15
    batch_size:int=32
    learning_rate:float=0.001
    seed:int=42
    width:int=24
    patience:int=6
    device:str='auto'


def _setup(cfg):
    import torch
    if not 1<=cfg.epochs<=500:raise ValueError('epochs out of range')
    if not 1<=cfg.batch_size<=512:raise ValueError('batch size out of range')
    if not 0<cfg.learning_rate<=.1:raise ValueError('learning rate out of range')
    if cfg.device not in ('auto','cpu','cuda'):raise ValueError('device must be auto/cpu/cuda')
    if cfg.device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA requested but not available')
    device='cuda' if cfg.device=='cuda' or (cfg.device=='auto' and torch.cuda.is_available()) else 'cpu'
    torch.manual_seed(cfg.seed);np.random.seed(cfg.seed);random.seed(cfg.seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(cfg.seed)
    # CPU deterministic paths: no hidden state from random batch order.
    try:torch.use_deterministic_algorithms(True,warn_only=True)
    except Exception:pass
    if device=='cpu':torch.set_num_threads(max(1,min(4,os.cpu_count() or 1)))
    return device


def _probabilities(net,data,device,batch_size=128):
    import torch
    net.eval();scores=[]
    with torch.inference_mode():
        for offset in range(0,len(data),batch_size):
            inp=torch.from_numpy(np.ascontiguousarray(data[offset:offset+batch_size,None,:])).to(device)
            scores.append(torch.sigmoid(net(inp)).cpu().numpy())
    return np.concatenate(scores).astype(float)


def _temperature(prob,y):
    """Fit post-hoc calibration using validation data ONLY."""
    from scipy.optimize import minimize_scalar
    from sklearn.metrics import log_loss
    eps=1e-6;p=np.clip(prob,eps,1-eps);logit=np.log(p/(1-p))
    def objective(log_t):
        calibrated=1/(1+np.exp(-np.clip(logit/np.exp(log_t),-50,50)))
        return float(log_loss(y,calibrated,labels=[0,1]))
    fit=minimize_scalar(objective,bounds=(-2,2),method='bounded')
    return float(np.exp(fit.x))


def _calibrate(prob,t):
    p=np.clip(np.asarray(prob,dtype=float),1e-6,1-1e-6)
    return 1/(1+np.exp(-np.clip(np.log(p/(1-p))/t,-50,50)))


def compute_metrics(y,p,threshold=.5,groups=None):
    from sklearn.metrics import balanced_accuracy_score,roc_auc_score,average_precision_score,brier_score_loss,confusion_matrix
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float)
    if len(y)!=len(p) or not len(y):raise ValueError('Empty or mismatched predictions')
    predicted=(p>=threshold).astype(int)
    matrix=confusion_matrix(y,predicted,labels=[0,1]).tolist()
    tn,fp=matrix[0];fn,tp=matrix[1]
    metrics={'n':int(len(y)), 'groups':int(len(set(groups))) if groups is not None else None,
             'positive_fraction':float(np.mean(y)), 'threshold':float(threshold),
             'confusion_matrix_0_1':matrix,'balanced_accuracy':float(balanced_accuracy_score(y,predicted)),
             'sensitivity_quality_acceptable':float(tp/(tp+fn)) if tp+fn else None,
             'specificity_quality_unacceptable':float(tn/(tn+fp)) if tn+fp else None,
             'brier':float(brier_score_loss(y,p)),
             'ece_10_bins':float(_ece(y,p)),
             'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
             'average_precision':float(average_precision_score(y,p)) if len(np.unique(y))==2 else None}
    return metrics


def _ece(y,p,bins=10):
    borders=np.linspace(0,1,bins+1);total=0.
    for j in range(bins):
        mask=(p>=borders[j]) & (p<=borders[j+1] if j==bins-1 else p<borders[j+1])
        if np.any(mask): total+=float(np.mean(mask))*abs(float(np.mean(y[mask]))-float(np.mean(p[mask])))
    return total


def bootstrap_auc_ci(y,p,groups,seed=42,repeats=200):
    """Group-bootstrap 95% CI, not a clinical confidence guarantee."""
    from sklearn.metrics import roc_auc_score
    rng=np.random.default_rng(seed);g=np.asarray(groups);y=np.asarray(y);p=np.asarray(p)
    unique=np.unique(g);est=[]
    for _ in range(repeats):
        sampled=rng.choice(unique,size=len(unique),replace=True)
        idx=np.concatenate([np.flatnonzero(g==part) for part in sampled])
        if len(np.unique(y[idx]))==2:est.append(float(roc_auc_score(y[idx],p[idx])))
    return [float(v) for v in np.percentile(est,[2.5,97.5])] if len(est)>=20 else None


def train_model(manifest,out_dir,config:TrainConfig|None=None,progress=None):
    """Train real CNN weights and evaluate with strict group-held-out test.

    Outputs: model.safetensors, model_card.json, report.json, metrics.csv,
    learning_curve.csv, split_assignments.csv, results_summary.md.
    """
    import torch
    from torch import nn
    from torch.utils.data import TensorDataset,DataLoader
    from sklearn.metrics import balanced_accuracy_score
    cfg=config or TrainConfig();device=_setup(cfg)
    cohort=load_cohort(manifest)
    train,val,test=split_by_group(cohort.y,cohort.groups,seed=cfg.seed)
    root=Path(out_dir).resolve();root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()):raise ValueError('Experiment output directory must be empty to preserve reproducibility')
    net=build_network(cfg.width).to(device)
    pos=float(cohort.y[train].sum()); neg=len(train)-pos
    criterion=nn.BCEWithLogitsLoss(pos_weight=torch.tensor([neg/max(pos,1)],device=device))
    optimizer=torch.optim.AdamW(net.parameters(),lr=cfg.learning_rate,weight_decay=1e-3)
    inputs=torch.from_numpy(np.ascontiguousarray(cohort.x[train,None,:]));labels=torch.from_numpy(cohort.y[train].astype(np.float32))
    loader=DataLoader(TensorDataset(inputs,labels),batch_size=cfg.batch_size,shuffle=True,generator=torch.Generator().manual_seed(cfg.seed))
    best=-1.;best_state=None;best_epoch=0;history=[];stale=0
    for epoch in range(1,cfg.epochs+1):
        net.train();losses=[]
        for x,y in loader:
            x=x.to(device);y=y.to(device);optimizer.zero_grad(set_to_none=True)
            logits=net(x);loss=criterion(logits,y)
            if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss; review input data and hyperparameters')
            loss.backward();nn.utils.clip_grad_norm_(net.parameters(),max_norm=5.)
            optimizer.step();losses.append(float(loss.item()))
        val_p=_probabilities(net,cohort.x[val],device)
        val_score=float(balanced_accuracy_score(cohort.y[val],val_p>=.5))
        history.append({'epoch':epoch,'train_loss':float(np.mean(losses)),'val_balanced_accuracy_at_0_5':val_score})
        if progress:progress(history[-1])
        if val_score>best+1e-6:
            best=val_score;best_epoch=epoch;stale=0
            best_state={k:v.detach().cpu().clone() for k,v in net.state_dict().items()}
        else:stale+=1
        if stale>=cfg.patience:break
    net.load_state_dict(best_state);net.to(device)
    vp=_probabilities(net,cohort.x[val],device)
    temp=_temperature(vp,cohort.y[val])
    vcal=_calibrate(vp,temp)
    # Choose threshold on validation ONLY (balanced accuracy), then lock it.
    thresholds=np.linspace(.15,.85,29)
    val_scores=[balanced_accuracy_score(cohort.y[val],vcal>=x) for x in thresholds]
    threshold=float(thresholds[int(np.argmax(val_scores))])
    tp=_calibrate(_probabilities(net,cohort.x[test],device),temp)
    test_metrics=compute_metrics(cohort.y[test],tp,threshold,cohort.groups[test])
    test_metrics['auc_95pct_group_bootstrap']=bootstrap_auc_ci(cohort.y[test],tp,cohort.groups[test],cfg.seed)
    slices={}
    for mod in sorted(set(cohort.modalities[test])):
        idx=cohort.modalities[test]==mod
        if idx.sum()>=3:slices[mod]=compute_metrics(cohort.y[test][idx],tp[idx],threshold,cohort.groups[test][idx])
    from safetensors.torch import save_file
    weights=root/'model.safetensors';save_file({k:v.contiguous() for k,v in best_state.items()},str(weights))
    from .registry import hash_file
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    card={'schema':SCHEMA,'created_utc':now,'research_only':True,'task':'HUMAN_LABELED_SIGNAL_QUALITY_RESEARCH',
          'not_for':['diagnosis','triage','alarm suppression','patient monitoring','clinical decisions'],
          'architecture':'wave_resnet_1d','width':cfg.width,'input_samples':512,'resample_hz':128,
          'label_mapping':{'0':'quality_unacceptable','1':'quality_acceptable'},
          'threshold_selected_on':'validation_only','threshold':threshold,'temperature_validation':temp,
          'dataset_manifest_sha256_and_size_fingerprint':cohort.fingerprint,'seed':cfg.seed,
          'weights_sha256':hash_file(weights),'train_config':asdict(cfg),'best_epoch':best_epoch}
    (root/'model_card.json').write_text(json.dumps(card,indent=2,allow_nan=False),encoding='utf-8')
    report={'kind':'RESEARCH_NOT_CLINICALLY_VALIDATED','created_utc':now,'config':asdict(cfg),
            'cohort_windows':int(len(cohort.y)),'cohort_groups':int(len(set(cohort.groups))),
            'train_windows':int(len(train)),'validation_windows':int(len(val)),'test_windows':int(len(test)),
            'n_train_groups':int(len(set(cohort.groups[train]))),'n_val_groups':int(len(set(cohort.groups[val]))),
            'n_test_groups':int(len(set(cohort.groups[test]))),
            'group_overlap':0,'best_epoch':best_epoch,'validation_selected_threshold':threshold,
            'validation_temperature':temp,'test_metrics':test_metrics,'by_modality_on_test':slices,
            'limitations':['Subject/record group assignments depend on correct manifest IDs',
                           'No independent external cohort evaluated',
                           'No clinical diagnosis or alarm claims',
                           'This is a retrospective test-split result, not a clinical trial']}
    (root/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    with (root/'learning_curve.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=list(history[0]));writer.writeheader();writer.writerows(history)
    with (root/'split_assignments.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.writer(f);writer.writerow(['row_index','group_id','split','label','modality'])
        membership={int(i):s for s,idx in [('train',train),('validation',val),('test',test)] for i in idx}
        for i,(g,y,m) in enumerate(zip(cohort.groups,cohort.y,cohort.modalities)):
            writer.writerow([i,g,membership[i],int(y),m])
    with (root/'metrics.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.writer(f);writer.writerow(['metric','value']);writer.writerows((k,json.dumps(v)) for k,v in test_metrics.items())
    md=['# VIGIL Studio Research Experiment','',f"- Dataset manifest: `{Path(manifest).name}`",f'- Group-disjoint train / validation / test: {len(train)} / {len(val)} / {len(test)} windows',f'- Final model selected at epoch: {best_epoch}',f'- Holdout ROC-AUC: {test_metrics["roc_auc"]}',f'- Holdout balanced accuracy: {test_metrics["balanced_accuracy"]:.4f}',f'- Holdout Brier score: {test_metrics["brier"]:.4f}',f'- Holdout group-bootstrap ROC-AUC 95% CI: {test_metrics["auc_95pct_group_bootstrap"]}','', '**Research-use only. Not a clinical trial, validated medical AI, or patient-care system.**']
    (root/'results_summary.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    return report


def load_trained_model(directory,device='cpu'):
    """Safe safetensors only; reject altered weights and unsafe pickle files."""
    import torch
    from safetensors.torch import load_file
    from .registry import hash_file
    root=Path(directory);card=json.loads((root/'model_card.json').read_text(encoding='utf-8'))
    if card.get('schema')!=SCHEMA or card.get('input_samples')!=512 or card.get('resample_hz')!=128:
        raise ValueError('Unexpected model schema or preprocessing specification')
    if hash_file(root/'model.safetensors')!=card.get('weights_sha256'):
        raise ValueError('Model weights integrity check failed')
    net=build_network(card['width']);net.load_state_dict(load_file(str(root/'model.safetensors'),device='cpu'),strict=True)
    net.to(device);net.eval()
    return net,card


def predict_waveform_quality(record,channel,model_dir,start_s=0,device='cpu'):
    import torch
    net,card=load_trained_model(model_dir,device=device)
    signal=extract_window(record,channel,start_s,card['input_samples'],card['resample_hz'])
    p=float(_calibrate(_probabilities(net,signal[None,:],device),card['temperature_validation'])[0])
    threshold=card['threshold']
    # No unsupported certainty or alarm condition label.
    return {'status':'EXPLORATORY_REVIEW_ONLY','quality_acceptable_score':p,
            'model_label':'QUALITY_ACCEPTABLE_RESEARCH' if p>=threshold else 'QUALITY_UNACCEPTABLE_RESEARCH',
            'threshold':threshold,'trained_on_manifest_fingerprint':card['dataset_manifest_sha256_and_size_fingerprint'],
            'warning':'Not a clinical probability, diagnosis, alert, or patient care decision'}
