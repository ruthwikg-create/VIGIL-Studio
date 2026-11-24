"""Produce nonclinical synthetic waveform fixtures for ENGINEERING TESTS ONLY.
Do NOT use these labels or results in clinical research or papers.
"""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
import numpy as np

def create(root:Path,n_groups=12):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(817)
    rows=[]
    for group in range(n_groups):
        fs=128;windows=[]
        for segment in range(4):
            t=np.arange(512)/fs
            if segment%2==0:
                sig=np.sin(2*np.pi*(1.1+.05*(group%3))*t)+.02*rng.standard_normal(len(t))
            else:
                sig=.1*np.sin(2*np.pi*.9*t)+1.2*rng.standard_normal(len(t))
            windows.append(sig)
        wave=np.concatenate(windows)
        path=root/f'synthetic_group_{group:02}.npz'
        meta={'name':f'synthetic_group_{group:02}','fs':fs,'origin':'SYNTHETIC_NOT_CLINICAL_DATA','sha256':'test_only','annotation':{}}
        np.savez_compressed(path,__meta__=np.asarray(json.dumps(meta)),ch_ECG=wave)
        for j in range(4):rows.append({'path':path.name,'group_id':f'SYNTH_{group:02}','label':1 if j%2==0 else 0,'channel':'ECG','fs':'','start_s':j*4,'modality':'ECG'})
    manifest=root/'manifest_SYNTHETIC_ENGINEERING_TEST_ONLY.csv'
    with manifest.open('w',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['path','group_id','label','channel','fs','start_s','modality'])
        writer.writeheader();writer.writerows(rows)
    return manifest

if __name__=='__main__':
    dest=Path(sys.argv[1]) if len(sys.argv)>1 else Path('examples/synthetic_ai_cohort')
    print('SYNTHETIC engineering test manifest:',create(dest))
