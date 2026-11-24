"""Reproducible *engineering stress tests* for biomedical signal pipelines.

Perturbed waveforms do not become clinical ground truth. Reports measure how
research descriptors change under seeded artifacts, NOT sensitivity or safety.
"""
from __future__ import annotations
import datetime, json
from pathlib import Path
import numpy as np
from ..core.records import Record
from ..core.processing import window_features,normalized_type

class StressTestError(ValueError):pass

ARTIFACTS=('unaltered','baseline_drift','powerline_50hz','powerline_60hz',
           'dropout_10pct','flatline_20pct','gain_x2','motion_bursts')

def perturb(x,fs,artifact,seed=42):
    x=np.asarray(x,dtype=np.float64)
    if artifact not in ARTIFACTS:raise StressTestError('Unknown artifact')
    if x.ndim!=1 or len(x)<32 or not 2<=fs<=5000:raise StressTestError('Expected valid one-dimensional signal')
    y=x.copy();finite=y[np.isfinite(y)]
    amplitude=float(np.percentile(finite,95)-np.percentile(finite,5)) if len(finite) else 1.
    amplitude=max(amplitude,0.01)
    t=np.arange(len(y))/fs
    rng=np.random.default_rng(seed)
    if artifact=='baseline_drift':y+=amplitude*.55*np.sin(2*np.pi*.2*t)
    elif artifact=='powerline_50hz':
        if fs<=100:raise StressTestError('Sampling rate too low to assess 50Hz powerline')
        y+=amplitude*.3*np.sin(2*np.pi*50*t)
    elif artifact=='powerline_60hz':
        if fs<=120:raise StressTestError('Sampling rate too low to assess 60Hz powerline')
        y+=amplitude*.3*np.sin(2*np.pi*60*t)
    elif artifact=='dropout_10pct':
        a=int(len(y)*.45);b=min(len(y),a+max(1,int(len(y)*.1)));y[a:b]=np.nan
    elif artifact=='flatline_20pct':
        a=int(len(y)*.4);b=min(len(y),a+max(1,int(len(y)*.2)))
        y[a:b]=float(np.nanmedian(y)) if np.isfinite(y).any() else 0.
    elif artifact=='gain_x2':y*=2
    elif artifact=='motion_bursts':
        n=max(1,int(len(y)*.05));idx=rng.choice(len(y),size=n,replace=False)
        y[idx]+=rng.normal(0,amplitude*2,size=n)
    return y

def stress_test(record:Record,channel:str,*,start_s=0,seconds=8,seed=42,model_dir=None):
    if channel not in record.channels:raise StressTestError(f'Channel not found: {channel}')
    if seconds<2 or seconds>60 or start_s<0:raise StressTestError('Use 2–60 seconds and nonnegative start time')
    a=round(start_s*record.fs);b=min(record.n,a+int(seconds*record.fs))
    if b-a<int(2*record.fs):raise StressTestError('Insufficient signal samples')
    original=record.channels[channel][a:b]
    kind=normalized_type(channel)
    rows=[]
    for artifact in ARTIFACTS:
        try:
            y=perturb(original,record.fs,artifact,seed)
        except StressTestError as e:
            rows.append({'artifact':artifact,'skipped':str(e)});continue
        seconds_used=len(y)/record.fs
        features=window_features(y,record.fs,0,seconds_used,kind)
        if features is None:continue
        row={'artifact':artifact,'quality_score_heuristic':features['quality_score'],
             'nonfinite_fraction':features['nonfinite_fraction'],
             'flatline_fraction':features['flatline_fraction'],
             'derivative_rms':features['derivative_rms'],
             'dynamic_range':features['dynamic_range'],
             'human_quality_ground_truth':None,
             'artifact_source':'SEEDED_IN_SILICO_STRESS_TEST'}
        if model_dir is not None:
            from ..ai.experiment import predict_waveform_quality
            rec=Record({channel:y},record.fs,'STRESS_TEST', 'IN_SILICO_PERTURBATION','')
            try:
                out=predict_waveform_quality(rec,channel,model_dir,0)
                row['neural_model_output']=out
            except Exception as exc:
                row['model_error']=str(exc)
        rows.append(row)
    return {'kind':'ENGINEERING_STRESS_TEST_NOT_CLINICAL_VALIDATION',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'record_sha256':record.sha256,'channel':channel,'fs_hz':record.fs,
            'seed':seed,'start_seconds':start_s,'sample_count':b-a,
            'description':'Seeded signal perturbations; NO independent clinical labels or sensitivity estimates',
            'results':rows}

def save_stress_report(report,output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,allow_nan=False,default=str),encoding='utf-8')
    return output
