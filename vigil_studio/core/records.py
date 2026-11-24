from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import hashlib, json, zipfile
import numpy as np

MAX_SAMPLES = 8_000_000
MAX_CHANNELS = 24

@dataclass
class Record:
    channels: dict[str, np.ndarray]
    fs: float
    name: str
    origin: str
    sha256: str
    annotation: dict = field(default_factory=dict)
    id: str = ''

    def __post_init__(self):
        self.fs=float(self.fs)
        if not 2 <= self.fs <= 5000: raise ValueError('Sampling rate must be 2–5000 Hz')
        if not self.channels or len(self.channels)>MAX_CHANNELS: raise ValueError('1–24 channels required')
        self.channels={str(k)[:70]:np.asarray(v,dtype=np.float64) for k,v in self.channels.items()}
        lengths={len(v) for v in self.channels.values()}
        if len(lengths)!=1 or not 32 <= next(iter(lengths)) <= MAX_SAMPLES:
            raise ValueError('Channels must have the same length (32 to 8 million points)')
        if not self.sha256:
            h=hashlib.sha256()
            for k,v in sorted(self.channels.items()): h.update(k.encode()); h.update(v.tobytes())
            self.sha256=h.hexdigest()

    @property
    def n(self): return len(next(iter(self.channels.values())))
    @property
    def duration(self): return self.n/self.fs
    def metadata(self):
        return {"name":self.name,"fs":self.fs,"channels":list(self.channels),"samples":self.n,
                "duration_s":round(self.duration,3),"origin":self.origin,"sha256":self.sha256,
                "annotation":self.annotation}

def record_from_npz(path:Path)->Record:
    p=Path(path)
    # NPZ is ZIP: reject oversized or suspicious archives before parsing any arrays.
    # This is an input-safety limit, not a guarantee against resource exhaustion.
    if p.stat().st_size > 2_100_000_000:
        raise ValueError('NPZ exceeds allowed compressed size')
    with zipfile.ZipFile(p) as z:
        members=z.infolist()
        if len(members)>MAX_CHANNELS+1:
            raise ValueError('NPZ has too many entries')
        names=[i.filename for i in members]
        if len(names)!=len(set(names)) or '__meta__.npy' not in names:
            raise ValueError('NPZ metadata missing or duplicate entries')
        if any(not (n=='__meta__.npy' or (n.startswith('ch_') and n.endswith('.npy'))) for n in names):
            raise ValueError('Unexpected NPZ entry')
        total=sum(i.file_size for i in members)
        if total>MAX_CHANNELS*MAX_SAMPLES*8+2_000_000 or total<=0:
            raise ValueError('NPZ decompressed content exceeds safe bound')
        if z.getinfo('__meta__.npy').file_size > 1_000_000:
            raise ValueError('NPZ metadata too large')
        if any(i.file_size>MAX_SAMPLES*8+4_000_000 for i in members if i.filename!='__meta__.npy'):
            raise ValueError('NPZ channel data too large')
    with np.load(p,allow_pickle=False) as data:
        meta=json.loads(str(data['__meta__']))
        channels={key[3:]:data[key].astype(float) for key in data.files if key.startswith('ch_')}
    return Record(channels=channels,fs=meta['fs'],name=meta['name'],origin=meta['origin'],
                  sha256=meta['sha256'],annotation=meta.get('annotation',{}))

def record_to_npz(rec:Record,path:Path):
    meta=rec.metadata()
    arrays={'__meta__':np.asarray(json.dumps(meta,allow_nan=False))}
    arrays.update({'ch_'+k: v for k,v in rec.channels.items()})
    np.savez_compressed(path,**arrays)
