"""Exploratory signal analysis. Algorithms and thresholds are NOT medically validated."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy import signal
from .records import Record
from .signal_quality_v01 import quality_features,estimate_rate

ENGINE_VERSION='vigil-signal-1.0'

def normalized_type(name:str)->str:
    n=''.join(c for c in name.upper() if c.isalnum())
    if n in {'ECG','EKG','II','MLII','V1','V2','V3','V4','V5','V6','LEADII','ECGII'} or 'ECG' in n: return 'ECG'
    if n in {'PPG','PLETH','SPO2','PLETHYSMOGRAM'} or 'PLETH' in n: return 'PPG'
    if n in {'ABP','ART','BP','ARTERIAL'} or 'ABP' in n: return 'ABP'
    if 'RESP' in n or n in {'RESP','BREATH'}: return 'RESP'
    if n.startswith('EEG'):return 'EEG'
    if n.startswith('EMG'):return 'EMG'
    return 'OTHER'

def _valid(x):return np.asarray(x,dtype=float)

def filter_trace(x,fs,mode='raw',notch_hz=0):
    """Zero-phase offline filtering for *review only*; no real-time interpretation."""
    x=_valid(x)
    if mode=='raw' and not notch_hz:return x.copy()
    mask=np.isfinite(x)
    if mask.sum()<max(16,int(fs)):return x.copy()
    # Avoid bridging sensor dropout: process each contiguous finite segment.
    result=x.copy()
    edges=np.diff(np.r_[False,mask,False].astype(int)); starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1)
    hi=min(fs*0.45,40.)
    if mode in ('ecg','ppg','abp','resp','general'):
        bands={'ecg':(0.5,hi),'ppg':(0.3,min(12,fs*0.45)),'abp':(0.3,min(20,fs*0.45)),
               'resp':(0.08,min(2.5,fs*0.45)),'general':(0.2,hi)}
        lo,hi=bands[mode]
        sos=signal.butter(3,[lo,hi],btype='bandpass',fs=fs,output='sos') if hi>lo*1.2 else None
    else: sos=None
    for a,b in zip(starts,ends):
        s=x[a:b].copy()
        if len(s)<max(20,int(fs*.8)):continue
        if notch_hz and 0<notch_hz<fs/2 and len(s)>fs:
            bn,an=signal.iirnotch(notch_hz,Q=25,fs=fs)
            pad=3*max(len(an),len(bn))
            if len(s)>pad:s=signal.filtfilt(bn,an,s)
        if sos is not None and len(s)>35:
            try:s=signal.sosfiltfilt(sos,s)
            except ValueError: pass
        result[a:b]=s
    return result

def detect_peaks(x,fs,kind='ECG'):
    """Exploratory maxima locations; not a validated QRS detector."""
    x=_valid(x)
    if len(x)<int(fs*3) or not np.isfinite(x).all():return np.array([],dtype=int)
    kind=normalized_type(kind)
    centered=signal.detrend(x)
    span=float(np.percentile(centered,95)-np.percentile(centered,5))
    if span<1e-8:return np.array([],dtype=int)
    distance=max(2,int(fs*(0.3 if kind=='ECG' else 0.35)))
    options=[]
    for polarity in ([1,-1] if kind=='ECG' else [1]):
        peaks,_=signal.find_peaks(centered*polarity,distance=distance,prominence=span*.33)
        if len(peaks)>=3:
            rr=np.diff(peaks)/fs
            bpm=60/np.median(rr)
            if 30<=bpm<=220:
                cv=np.std(rr)/max(1e-10,np.mean(rr))
                options.append((cv,-len(peaks),peaks))
    return min(options,key=lambda z:(z[0],z[1]))[2] if options else np.array([],dtype=int)

def hrv_features(peaks,fs):
    """Unvalidated time-domain RR variability summary; NOT an HRV diagnostic."""
    if len(peaks)<5:return {'median_bpm':None,'sdnn_ms':None,'rmssd_ms':None,'n_intervals':max(0,len(peaks)-1)}
    rr=np.diff(peaks)/fs
    # Exclude intervals outside exploratory bounds; this selection introduces bias.
    rr=rr[(rr>=0.3)&(rr<=2.0)]
    if len(rr)<4:return {'median_bpm':None,'sdnn_ms':None,'rmssd_ms':None,'n_intervals':int(len(rr))}
    return {'median_bpm':round(float(60/np.median(rr)),2),
            'sdnn_ms':round(float(np.std(rr,ddof=1)*1000),2),
            'rmssd_ms':round(float(np.sqrt(np.mean(np.diff(rr)**2))*1000),2),
            'n_intervals':int(len(rr))}

def spectrum(x,fs,max_points=256):
    x=_valid(x)
    if np.isfinite(x).sum()<32:return {'freq_hz':[],'power':[],'dominant_hz':None}
    # Preserve missingness: spectrum explicitly not estimated for heavily incomplete records.
    if np.isfinite(x).mean()<0.9:return {'freq_hz':[],'power':[],'dominant_hz':None}
    idx=np.arange(len(x));mask=np.isfinite(x)
    x=np.interp(idx,idx[mask],x[mask]);f,p=signal.welch(x,fs=fs,nperseg=min(len(x),2048))
    valid=(f>0.05)&(f<=min(70,fs/2))
    dom=float(f[valid][np.argmax(p[valid])]) if valid.any() else None
    step=max(1,int(np.ceil(len(f)/max_points)))
    return {'freq_hz':np.round(f[::step],4).tolist(),'power':np.round(p[::step],9).tolist(),
            'dominant_hz':round(dom,3) if dom is not None else None}

def window_features(x,fs,start,end,kind):
    seg=_valid(x)[int(start*fs):int(end*fs)]
    if len(seg)<16:return None
    q=quality_features(seg.tolist(),fs)
    finite=seg[np.isfinite(seg)]
    span=float(np.percentile(finite,99)-np.percentile(finite,1)) if len(finite)>10 else 0
    derivatives=np.diff(seg);derivatives=derivatives[np.isfinite(derivatives)]
    vals={'availability':float(q['availability']),'flatline_fraction':float(q['flatline_fraction']),
          'high_frequency_fraction':float(q.get('high_frequency_fraction') or 0),
          'dynamic_range':float(q['dynamic_range']),'quality_score':float(q['quality_score']),
          'std':float(np.std(finite)) if len(finite) else 0.0,
          'mad':float(np.median(np.abs(finite-np.median(finite)))) if len(finite) else 0.0,
          'derivative_rms':float(np.sqrt(np.mean(derivatives**2))) if len(derivatives) else 0.0,
          'range_99_1':span, 'nonfinite_fraction':1-float(q['availability']),
          'start_s':float(start),'end_s':float(end),'kind':kind,
          'flags':q['flags'],'label':q['label']}
    return vals

FEATURE_FIELDS=['availability','flatline_fraction','high_frequency_fraction','dynamic_range','std','mad','derivative_rms','range_99_1','nonfinite_fraction']

def analyze_record(rec:Record,window_s=8.,stride_s=4.,max_windows=10000):
    if not 1<=window_s<=120 or not 0.25<=stride_s<=window_s:
        raise ValueError('Window must be 1–120s and stride 0.25s to window length')
    results={};rates=[]
    for name,x in rec.channels.items():
        kind=normalized_type(name)
        q=quality_features(x.tolist(),rec.fs)
        rate=estimate_rate(x.tolist(),rec.fs,kind)
        peaks=detect_peaks(x,rec.fs,kind) if kind in ('ECG','PPG','ABP') else np.array([],dtype=int)
        hrv=hrv_features(peaks,rec.fs) if kind=='ECG' else None
        spec=spectrum(x,rec.fs)
        windows=[]
        if rec.duration>=window_s:
            n=min(max_windows,int(np.floor((rec.duration-window_s)/stride_s))+1)
            for i in range(n):
                a=i*stride_s;v=window_features(x,rec.fs,a,min(rec.duration,a+window_s),kind)
                if v: windows.append(v)
        # Annotated beat counts if source data includes annotations; not used as inferred truth.
        results[name]={'kind':kind,'quality':q,'rate':rate,'hrv':hrv,'spectrum':spec,
                       'peaks_count':len(peaks),'windows':windows,
                       'missing_samples':int(np.count_nonzero(~np.isfinite(x)))}
        if kind in ('ECG','PPG','ABP') and q['quality_score']>=0.7 and rate.get('estimated_bpm') is not None:
            rates.append((name,float(rate['estimated_bpm'])))
    diffs=[{'channel_a':a,'channel_b':b,'difference_bpm':round(abs(v-u),2)}
           for i,(a,v) in enumerate(rates) for b,u in rates[i+1:]]
    if not diffs: decision='INSUFFICIENT_EVIDENCE'
    elif max(d['difference_bpm'] for d in diffs)>12: decision='DISCORDANT_EXPLORATORY'
    else: decision='EXPLORATORY_AGREEMENT'
    from .modalities import feature_report
    return {'engine':ENGINE_VERSION,'record':rec.metadata(),'channels':results,'modality_features':feature_report(rec),'comparisons':diffs,
            'overall':decision,'limitations':[
                'All quality scores, filters, peak/rate estimates and thresholds are research-only, unvalidated.',
                'Agreement cannot rule out arrhythmia or justify suppressing alarms.',
                'Missing data, sensor faults, amplitude units and domain shift can invalidate estimates.',
                'No diagnosis, clinical decision support, or medical-device clearance is claimed.']}
