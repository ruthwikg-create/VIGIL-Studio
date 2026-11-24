"""Distinctly marked synthetic waveforms, *never* used as clinical evidence."""
import hashlib
import numpy as np
from .records import Record

def make_demo(case='baseline',fs=250.,seconds=45.,seed=14):
    if case not in ('baseline','motion_artifact','dropout','discordant'):
        raise ValueError('Unknown synthetic demo mode')
    n=int(fs*seconds);t=np.arange(n)/fs;rng=np.random.default_rng(seed)
    # Illustrative waveforms; not an electrophysiological patient simulator.
    ecg=0.015*rng.normal(size=n)+0.025*np.sin(2*np.pi*0.25*t)
    r_times=np.arange(.65,seconds,0.82)
    for r in r_times:
        dt=t-r
        ecg+=1.0*np.exp(-0.5*(dt/.012)**2) -0.18*np.exp(-0.5*((dt+.025)/.018)**2)
        ecg+=.24*np.exp(-0.5*((dt-.19)/.06)**2)
    def pulse(times):
        y=0.02*rng.normal(size=n)
        for r in times:
            dt=t-(r+.21)
            y+=1.2*(np.maximum(dt,0)/.12)**2*np.exp(-np.maximum(dt,0)/.12)*np.logical_and(dt>=0,dt<1.)
        return y
    ppg=pulse(r_times);abp=75+24*pulse(r_times)
    resp=.8*np.sin(2*np.pi*0.23*t)+.02*rng.normal(size=n)
    if case=='motion_artifact':
        k=(t>seconds*.35)&(t<seconds*.57)
        ecg[k]+=1.5*rng.normal(size=k.sum());ppg[k]+=.7*rng.normal(size=k.sum())
    elif case=='dropout':
        k=(t>seconds*.35)&(t<seconds*.55)
        ecg[k]=np.nan;ppg[k]=np.nan
    elif case=='discordant':
        ppg=pulse(np.arange(.65,seconds,.5))
    channels={'ECG':ecg,'PPG':ppg,'ABP':abp,'RESP':resp}
    return Record(channels,fs,'SYNTHETIC_'+case.upper(), 'SYNTHETIC_NOT_CLINICAL_DATA',
                  hashlib.sha256((case+str(seed)+str(fs)+str(seconds)).encode()).hexdigest(),
                  annotation={'dataset':'SYNTHETIC_ONLY','purpose':'UI and automated-test fixture'})
