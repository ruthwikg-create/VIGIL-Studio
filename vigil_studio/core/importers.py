"""Read controlled local research files; no automatic network requests."""
from __future__ import annotations
from pathlib import Path
import csv,hashlib,math,re
import numpy as np
from .records import Record,MAX_SAMPLES,MAX_CHANNELS

FORBIDDEN={'patient','patient_id','patientid','patientname','patient_name','patient_id','name','dob','date_of_birth','dateofbirth','birthdate','mrn','medicalrecordnumber','hospitalid','ssn','aadhaar','aadhar','email','phone','address'}

def read_csv(path:Path,fs:float|None=None)->Record:
    path=Path(path)
    if path.stat().st_size > 300*1024*1024: raise ValueError('CSV over 300 MB; use a smaller segment')
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        r=csv.reader(f)
        headers=next(r,None)
        if not headers: raise ValueError('Empty file / missing header')
        normalized=[re.sub('[^a-z0-9_]+','',h.lower().strip()) for h in headers]
        if any(h in FORBIDDEN for h in normalized):
            raise ValueError('Potential personal-identifier column. De-identify before import.')
        if len(normalized)!=len(set(normalized)) or len(headers)>MAX_CHANNELS+1:
            raise ValueError('Duplicate headers or too many channels')
        tidx=next((i for i,h in enumerate(normalized) if h in ('time','time_s','seconds')),None)
        cols=[i for i in range(len(headers)) if i!=tidx]
        if not cols: raise ValueError('No numerical signal columns')
        values=[[] for _ in headers]
        for line,row in enumerate(r,2):
            if line>MAX_SAMPLES+1 or (line-1)*len(headers)>16_000_000:
                raise ValueError('CSV memory-safe cell limit exceeded; import a smaller segment')
            if len(row)!=len(headers): raise ValueError(f'Column mismatch on row {line}')
            for i,cell in enumerate(row):
                try: v=float(cell) if cell.strip() else float('nan')
                except ValueError as e: raise ValueError(f'Non-numeric column on row {line}') from e
                values[i].append(v)
    if tidx is not None:
        t=np.asarray(values[tidx],dtype=float)
        d=np.diff(t)
        if not np.all(np.isfinite(d)) or np.any(d<=0): raise ValueError('Time coordinates must increase')
        inferred=1/float(np.median(d))
        if fs is None: fs=inferred
        if abs(fs-inferred)/inferred > 0.05: raise ValueError('Sample rate and time column disagree')
        if np.max(d) > 1.5*np.median(d): raise ValueError('Irregular sampling; resample externally')
    if fs is None: raise ValueError('Sampling frequency required for CSV without time column')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    # Avoid accidental reuse of a file's personal name as exported case ID.
    return Record({headers[i].strip():np.array(values[i]) for i in cols},fs,path.name,'local_csv',digest)

def read_wfdb(path:Path,max_seconds:float|None=None)->Record:
    try: import wfdb
    except ImportError as e: raise RuntimeError('WFDB support needs: pip install wfdb') from e
    path=Path(path)
    stem=path.with_suffix('') if path.suffix.lower() in ('.hea','.dat') else path
    header=wfdb.rdheader(str(stem))
    end=min(int(header.sig_len),MAX_SAMPLES) if max_seconds is None else min(int(header.fs*max_seconds),int(header.sig_len),MAX_SAMPLES)
    if end < 32: raise ValueError('Insufficient signal samples')
    r=wfdb.rdrecord(str(stem),sampfrom=0,sampto=end)
    data=np.asarray(r.p_signal,dtype=float)
    if data.ndim!=2: raise ValueError('Invalid WFDB record')
    channels={str(name):data[:,i] for i,name in enumerate(r.sig_name[:MAX_CHANNELS])}
    header_file=stem.with_suffix('.hea')
    # The local record identity includes waveform bytes rather than only the small header.
    h=hashlib.sha256()
    for local in (header_file,stem.with_suffix('.dat')):
        if local.is_file():
            with local.open('rb') as fp:
                for block in iter(lambda:fp.read(1024*1024),b''): h.update(block)
    digest=h.hexdigest()
    anns={}
    for name in ('atr','qrs'):
        try:
            ann=wfdb.rdann(str(stem),name,sampfrom=0,sampto=end)
            annfile=stem.with_suffix('.'+name)
            ann_sha=hashlib.sha256(annfile.read_bytes()).hexdigest() if annfile.is_file() else None
            anns={'source':name,'sample':ann.sample.astype(int).tolist(), 'symbol':list(ann.symbol), 'file_sha256':ann_sha}
            break
        except (FileNotFoundError,ValueError,IOError): pass
    return Record(channels,float(r.fs),stem.name,'local_wfdb',digest,annotation=anns)

def read_edf(path:Path,max_seconds:float=300)->Record:
    try: import mne
    except ImportError as e: raise RuntimeError('EDF support needs: pip install mne') from e
    raw=mne.io.read_raw_edf(str(path),preload=False,verbose='ERROR')
    try:
        fs=float(raw.info['sfreq']); limit=min(raw.n_times,int(max_seconds*fs),MAX_SAMPLES)
        x=raw.get_data(start=0,stop=limit,picks=list(range(min(len(raw.ch_names),MAX_CHANNELS))))
        channels={name:x[i] for i,name in enumerate(raw.ch_names[:x.shape[0]])}
        return Record(channels,fs,Path(path).name,'local_edf',hashlib.sha256(Path(path).read_bytes()).hexdigest())
    finally: raw.close()

def open_record(path:Path,fs:float|None=None,max_seconds:float|None=None)->Record:
    path=Path(path)
    if not path.is_file(): raise FileNotFoundError(str(path))
    suffix=path.suffix.lower()
    if suffix=='.csv': return read_csv(path,fs)
    if suffix in ('.hea','.dat'): return read_wfdb(path,max_seconds)
    if suffix in ('.edf','.bdf'): return read_edf(path,max_seconds)
    if suffix=='.npz':
        from .records import record_from_npz
        return record_from_npz(path)
    raise ValueError('Supported imports: CSV, WFDB (.hea/.dat), EDF/BDF, VIGIL NPZ')
