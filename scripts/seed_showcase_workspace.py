"""Populate a local workspace with synthetic, explicitly non-clinical demo recordings.
Do not run this script against a hospital or personal research workspace.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from vigil_studio.core.demo import make_demo
from vigil_studio.core.records import Record
from vigil_studio.core.processing import analyze_record
from vigil_studio.core.store import Workspace

def build(showcase_dir:Path)->tuple[Workspace,dict]:
    showcase_dir=Path(showcase_dir).resolve()
    showcase_dir.mkdir(parents=True,exist_ok=True)
    ws=Workspace(showcase_dir)
    existing={c['name']:c['id'] for c in ws.list_cases()}
    ids={}
    for mode in ('baseline','motion_artifact','dropout','discordant'):
        rec=make_demo(case=mode,seconds=45.,seed=14)
        ids[rec.name]=existing.get(rec.name) or ws.add_case(rec,analyze_record(rec))
    name='SYNTHETIC_EEG_EMG_EXPLORATION'
    if name not in existing:
        fs=256.; t=np.arange(40*256)/fs; rng=np.random.default_rng(102)
        eeg=16e-6*np.sin(2*np.pi*10*t)+9e-6*np.sin(2*np.pi*6*t)+3e-6*rng.standard_normal(t.size)
        emg=0.05*rng.standard_normal(t.size)*(0.2+0.8*(np.sin(2*np.pi*.25*t)>0))
        resp=.7*np.sin(2*np.pi*.24*t)+.03*rng.standard_normal(t.size)
        sha=hashlib.sha256(b'SYNTHETIC_EEG_EMG_EXPLORATION_SEED102').hexdigest()
        rec=Record({'EEG':eeg,'EMG':emg,'RESP':resp},fs,name,'SYNTHETIC_NOT_CLINICAL_DATA',sha,{'purpose':'Showcase visualization only','review_status':'NOT independently reviewed'})
        ids[name]=ws.add_case(rec,analyze_record(rec))
    else:ids[name]=existing[name]
    return ws,ids

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,default=Path(__file__).resolve().parents[1]/'SHOWCASE'/'demo_workspace')
    args=parser.parse_args()
    ws,ids=build(args.workspace)
    print(f'Prepared {len(ids)} SYNTHETIC examples under {ws.root}')
    print('No real patient data, no clinical model claims. Existing cases are not overwritten.')
