"""Explicitly labelled local waveform cohorts with group-level leakage controls.

The manifest is a CSV with path,group_id,label,channel,fs,start_s,modality.
All paths must be relative to the manifest directory; no implicit file discovery.
Labels are independently assigned HUMAN signal quality labels (0=unacceptable,
1=acceptable), NOT disease diagnoses or alarm truth labels.
"""
from __future__ import annotations
import csv, hashlib, json, math, re
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
from fractions import Fraction
from ..core.importers import open_record

EXPECTED = ('path','group_id','label','channel','fs','start_s','modality')
MODALITIES = {'ECG','EEG','EMG','PPG','ABP','RESP','OTHER'}

class DatasetError(ValueError): pass

@dataclass(frozen=True)
class WaveSample:
    path: Path
    group_id: str
    label: int
    channel: str
    fs: float|None
    start_s: float
    modality: str

@dataclass
class Cohort:
    x: np.ndarray
    y: np.ndarray
    groups: np.ndarray
    modalities: np.ndarray
    fingerprint: str
    entries: list[WaveSample]


def load_manifest(path: str|Path, max_rows=100000) -> tuple[list[WaveSample],str]:
    p=Path(path).resolve()
    if not p.is_file() or p.stat().st_size>25*1024*1024: raise DatasetError('Missing or too-large manifest')
    raw=p.read_bytes(); root=p.parent
    entries=[]
    with p.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not set(EXPECTED).issubset(reader.fieldnames or []): raise DatasetError('Expected columns: '+', '.join(EXPECTED))
        for i,row in enumerate(reader,2):
            if i>max_rows+1: raise DatasetError('Cohort exceeds configured row limit')
            relative=Path(row['path'])
            if relative.is_absolute() or '..' in relative.parts or not relative.parts:
                raise DatasetError(f'Row {i}: dataset paths must remain within manifest folder')
            loc=(root/relative).resolve()
            if not loc.is_relative_to(root): raise DatasetError(f'Row {i}: path leaves cohort directory')
            if not loc.is_file(): raise DatasetError(f'Row {i}: missing file: {relative}')
            if loc.suffix.lower() not in ('.npz','.csv','.edf','.bdf','.hea','.dat'):
                raise DatasetError(f'Row {i}: unsupported format')
            group=row['group_id'].strip()
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',group): raise DatasetError(f'Row {i}: invalid anonymized group_id')
            if row['label'].strip() not in ('0','1'): raise DatasetError(f'Row {i}: label must be 0 or 1, not model-derived')
            mod=row['modality'].strip().upper()
            if mod not in MODALITIES: raise DatasetError(f'Row {i}: unknown modality')
            try:
                fs=float(row['fs']) if row['fs'].strip() else None
                start=float(row['start_s'])
            except ValueError as ex: raise DatasetError(f'Row {i}: invalid fs/start_s') from ex
            if fs is not None and (not math.isfinite(fs) or not 2<=fs<=5000):raise DatasetError(f'Row {i}: fs out of range')
            if not math.isfinite(start) or not 0<=start<=86400: raise DatasetError(f'Row {i}: start_s out of range')
            entries.append(WaveSample(loc,group,int(row['label']),row['channel'].strip(),fs,start,mod))
    if not entries: raise DatasetError('Empty manifest')
    # If an identical source file is assigned different group IDs, a random split
    # would leak source identity across train/validation/test.
    seen={}
    for e in entries:
        old=seen.setdefault(e.path,e.group_id)
        if old!=e.group_id:raise DatasetError('Same source file appears under multiple group IDs')
    return entries,hashlib.sha256(raw).hexdigest()


def extract_window(record, channel:str, start_s:float, target_length:int=512, target_fs:int=128):
    if channel not in record.channels:raise DatasetError(f'Channel {channel!r} absent from waveform')
    if target_length<32 or target_length>8192 or target_fs<2 or target_fs>1000:
        raise DatasetError('Unsupported target sampling configuration')
    fs=record.fs
    source_start=int(round(start_s*fs));source_len=int(math.ceil(target_length*fs/target_fs))+4
    if source_start<0 or source_start>=record.n:raise DatasetError('Window starts outside recording')
    signal=np.asarray(record.channels[channel][source_start:min(record.n,source_start+source_len)],dtype=np.float64)
    needed=target_length*fs/target_fs
    if len(signal)<needed:raise DatasetError('Recording too short for requested window')
    ratio=Fraction(target_fs/fs).limit_denominator(1000)
    # Bounded polyphase anti-aliasing avoids unbounded interpolation precision.
    resampled=resample_poly(signal,int(ratio.numerator),int(ratio.denominator))
    if resampled.size<target_length:raise DatasetError('Resampled recording too short')
    signal=resampled[:target_length]
    valid=np.isfinite(signal)
    if valid.mean()<.8:raise DatasetError('Window has over 20% nonfinite samples')
    median=float(np.nanmedian(np.where(valid,signal,np.nan)))
    signal=np.where(valid,signal,median)
    scale=float(np.percentile(signal,75)-np.percentile(signal,25))
    if not math.isfinite(scale) or scale<1e-10:
        # Flatline windows are informative for signal-quality research, not removed.
        scale=1.0
    signal=np.clip((signal-median)/scale,-8,8).astype(np.float32)
    return signal


def load_cohort(path:str|Path, target_length:int=512,target_fs:int=128,max_rows:int=30000) -> Cohort:
    entries,raw_sha=load_manifest(path,max_rows)
    xs=[];ys=[];groups=[];mods=[];cache={}
    for idx,e in enumerate(entries,1):
        if e.path not in cache:cache[e.path]=open_record(e.path,fs=e.fs,max_seconds=86400)
        try:x=extract_window(cache[e.path],e.channel,e.start_s,target_length,target_fs)
        except Exception as exc:raise DatasetError(f'Row {idx+1}: {exc}') from exc
        xs.append(x);ys.append(e.label);groups.append(e.group_id);mods.append(e.modality)
    if len(xs)<30 or len(set(groups))<6 or len(set(ys))<2:
        raise DatasetError('Need at least 30 human-labelled windows, 6 independent groups, both classes')
    h=hashlib.sha256();h.update(raw_sha.encode())
    for e in entries: h.update(str(e.path.relative_to(Path(path).resolve().parent)).encode());h.update(e.path.stat().st_size.to_bytes(8,'big'))
    return Cohort(np.stack(xs),np.asarray(ys,dtype=np.int64),np.asarray(groups),np.asarray(mods),h.hexdigest(),entries)


def split_by_group(y,groups,seed=42):
    """A fixed train/validation/test split, group-disjoint; no silent fallback."""
    from sklearn.model_selection import GroupShuffleSplit
    if len(np.unique(groups))<6:raise DatasetError('At least 6 independent groups required')
    y=np.asarray(y);groups=np.asarray(groups)
    for attempt in range(80):
        outer=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=seed+attempt)
        trainval,test=next(outer.split(y,y,groups))
        inner=GroupShuffleSplit(n_splits=1,test_size=.25,random_state=seed+1000+attempt)
        sub,val=next(inner.split(y[trainval],y[trainval],groups[trainval]))
        train=trainval[sub];val=trainval[val]
        if all(len(set(y[k]))==2 for k in (train,val,test)) and all(len(k)>=3 for k in (train,val,test)):
            sets=[set(groups[k]) for k in (train,val,test)]
            assert not (sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
            return train,val,test
    raise DatasetError('Unable to form group-separated splits with both labels in every set; add more diverse groups')
