"""Exploratory biomedical modality features for research workflows.
No thresholds here have diagnostic meaning. A power ratio is not a clinical finding.
"""
from __future__ import annotations
import numpy as np
from scipy.signal import welch,find_peaks
from scipy.integrate import trapezoid
from .processing import normalized_type,detect_peaks,hrv_features


def _clean_segment(x):
    x=np.asarray(x,dtype=float)
    return x if np.isfinite(x).all() else x[np.isfinite(x)]

def band_powers(x,fs,bands):
    clean=_clean_segment(x)
    if len(clean)<max(64,int(fs*2)) or fs<=0:return {}
    f,p=welch(clean-np.median(clean),fs=fs,nperseg=min(len(clean),int(fs*4)))
    out={}
    for name,(low,high) in bands.items():
        mask=(f>=low)&(f<=high)&(f<=fs/2)
        out[name]=round(float(trapezoid(p[mask],f[mask])) if mask.sum()>1 else 0.0,9)
    return out

def eeg_features(x,fs):
    """EEG PSD is illustrative only; no artifact regression or montage reference supplied."""
    bands={'delta':(.5,4),'theta':(4,8),'alpha':(8,13),'beta':(13,30),'gamma':(30,45)}
    values=band_powers(x,fs,bands)
    total=sum(values.values())
    return {'absolute_bandpower':values,
            'relative_bandpower':{k:round(v/total,5) if total>0 else None for k,v in values.items()},
            'alpha_beta_ratio':round(values['alpha']/values['beta'],4) if values.get('beta',0)>0 else None,
            'limitations':'Requires electrode montage, referencing, artifact control and external validation'} if values else {}

def emg_features(x,fs):
    """EMG amplitude/spectral descriptors; not strength, fatigue diagnosis or recruitment estimates."""
    z=_clean_segment(x)
    if len(z)<max(64,int(fs)) or fs<20:return {}
    z=z-np.mean(z)
    crossings=int(np.count_nonzero((z[:-1]*z[1:]<0)&(np.abs(np.diff(z))>max(np.std(z)*.05,1e-9))))
    f,p=welch(z,fs=fs,nperseg=min(len(z),2048));mask=(f>=10)&(f<=min(fs/2,500))
    medium=None;mean=None
    if mask.sum()>2:
        ff=f[mask];pp=p[mask]
        power=pp.sum()
        if power>0:
            median_idx=np.searchsorted(np.cumsum(pp),.5*power)
            medium=float(ff[min(len(ff)-1,median_idx)])
            mean=float(np.sum(ff*pp)/power)
    return {'rms':round(float(np.sqrt(np.mean(z*z))),7),
            'mean_absolute_value':round(float(np.mean(np.abs(z))),7),
            'zero_crossings':crossings,
            'waveform_length':round(float(np.sum(np.abs(np.diff(z)))),6),
            'median_frequency_hz':round(medium,3) if medium is not None else None,
            'mean_frequency_hz':round(mean,3) if mean is not None else None,
            'limitations':'Amplitudes are unit-dependent; frequency metrics require proper EMG bandpass and acquisition settings'}

def respiration_features(x,fs):
    z=_clean_segment(x)
    if len(z)<fs*15:return {}
    f,p=welch(z-np.mean(z),fs=fs,nperseg=min(len(z),int(fs*60)))
    mask=(f>=.07)&(f<=.65)
    if not mask.any():return {}
    dom=float(f[mask][np.argmax(p[mask])])
    return {'dominant_resp_frequency_hz':round(dom,4),
            'exploratory_breaths_per_min':round(dom*60,2),
            'limitations':'Signal spectral maximum is not an authoritative measured respiratory rate'}

def pulse_arrival_features(ecg,ppg,fs):
    """Simple beat-lag exploration; not a blood pressure/PAT/PTT measurement."""
    e=detect_peaks(ecg,fs,'ECG');p=detect_peaks(ppg,fs,'PPG')
    if len(e)<4 or len(p)<4:return {}
    delays=[]
    for event in e:
        ix=np.searchsorted(p,event)
        if ix<len(p):
            dt=(p[ix]-event)/fs
            if .06<=dt<=.55:delays.append(dt)
    if len(delays)<4:return {}
    return {'median_ecg_ppg_peak_lag_ms':round(float(np.median(delays)*1000),2),
            'matched_events':len(delays),
            'limitations':'Not validated pulse arrival time; acquisition delays and peak morphology distort lag'}

def feature_report(record):
    result={}
    for ch,x in record.channels.items():
        kind=normalized_type(ch)
        if kind=='EEG':result[ch]=eeg_features(x,record.fs)
        elif kind=='EMG':result[ch]=emg_features(x,record.fs)
        elif kind=='RESP':result[ch]=respiration_features(x,record.fs)
        elif kind=='ECG':result[ch]={'exploratory_hrv':hrv_features(detect_peaks(x,record.fs,'ECG'),record.fs)}
        elif kind in ('PPG','ABP'):
            p=detect_peaks(x,record.fs,kind)
            result[ch]={'exploratory_pulse_peaks':int(len(p))}
        else:result[ch]={'generic_spectrum_only':True}
    ecg=next((v for k,v in record.channels.items() if normalized_type(k)=='ECG'),None)
    ppg=next((v for k,v in record.channels.items() if normalized_type(k)=='PPG'),None)
    pair=pulse_arrival_features(ecg,ppg,record.fs) if ecg is not None and ppg is not None else {}
    return {'channels':result,'ecg_ppg_lag':pair,
            'notice':'Exploratory research descriptors only; not for clinical interpretation'}
