"""Research-only QRS detector diagnostic against *real* beat annotations.
NOT a medical evaluation, not a classification benchmark, and not clinical evidence.
"""
import argparse,json
import numpy as np
from vigil_studio.core.importers import read_wfdb
from vigil_studio.core.processing import detect_peaks,normalized_type

BEATS=set('NLRaAJSejVErF/fQ') | {'A','S','F','J','e','j','V','E','/','f','Q','?'}

def match_events(reference,predicted,fs,tolerance_s=.15):
    """1-to-1 matching of peak indices with ± tolerance (not greedy multi-match)."""
    ref=np.sort(np.asarray(reference,dtype=int));pred=np.sort(np.asarray(predicted,dtype=int))
    tol=int(round(tolerance_s*fs));i=j=tp=0
    while i<len(ref) and j<len(pred):
        if abs(int(ref[i])-int(pred[j]))<=tol:tp+=1;i+=1;j+=1
        elif ref[i]<pred[j]:i+=1
        else:j+=1
    fp=len(pred)-tp;fn=len(ref)-tp
    return {'tp':int(tp),'fp':int(fp),'fn':int(fn),
            'precision':round(tp/(tp+fp),5) if tp+fp else None,
            'recall':round(tp/(tp+fn),5) if tp+fn else None,
            'f1':round(2*tp/(2*tp+fp+fn),5) if 2*tp+fp+fn else None}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('wfdb_record_stem');p.add_argument('--seconds',type=float,default=300)
    a=p.parse_args();rec=read_wfdb(a.wfdb_record_stem,max_seconds=a.seconds)
    ann=rec.annotation
    if not ann or ann.get('source')!='atr':raise SystemExit('Beat reference .atr annotations required')
    reference=[int(x) for x,symbol in zip(ann['sample'],ann['symbol']) if symbol in BEATS]
    channel=next((n for n in rec.channels if normalized_type(n)=='ECG'),None)
    if channel is None:raise SystemExit('No recognized ECG channel')
    pred=detect_peaks(rec.channels[channel],rec.fs,'ECG')
    result=match_events(reference,pred,rec.fs)
    print(json.dumps({'dataset':rec.name,'n_reference':len(reference),'n_pred':len(pred),
                      'channel':channel,'results':result,'disclaimer':'Research-only detector diagnostic, not clinical validation'},indent=2))
