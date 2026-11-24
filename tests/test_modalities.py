import numpy as np
from vigil_studio.core.records import Record
from vigil_studio.core.modalities import band_powers,eeg_features,emg_features,respiration_features,feature_report

def test_eeg_alpha_spectral_peak():
    fs=128;t=np.arange(fs*10)/fs;x=np.sin(2*np.pi*10*t)
    report=eeg_features(x,fs)
    assert report['absolute_bandpower']['alpha']>report['absolute_bandpower']['beta']

def test_emg_features_return_numeric():
    fs=1000;t=np.arange(fs*4)/fs;x=np.sin(2*np.pi*120*t)
    report=emg_features(x,fs)
    assert report['median_frequency_hz']>70
    assert report['rms']>.6

def test_resp_signal_spectrum():
    fs=50;t=np.arange(fs*60)/fs;x=np.sin(2*np.pi*.25*t)
    report=respiration_features(x,fs)
    assert abs(report['exploratory_breaths_per_min']-15)<1
