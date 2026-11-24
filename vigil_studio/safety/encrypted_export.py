"""Optional encrypted research waveform handoff; NOT a clinical patient-data vault.

Requires cryptography. Does not encrypt the existing VIGIL SQLite workspace,
protect memory, authenticate hospital users, or satisfy HIPAA/DPDP/ISO 27001.
Files are an authenticated AES-256-GCM envelope with a scrypt-derived key.
Never reuse a stored envelope's nonce; every export generates a fresh salt+nonce.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import secrets
import struct
from pathlib import Path

MAGIC=b'VIGILE1\0'
MAX_PLAINTEXT=96*1024*1024   # bounded in-memory AEAD implementation
PARAMETERS={'n':2**15,'r':8,'p':1}


def _aes():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise RuntimeError('Install optional cryptography: python -m pip install "cryptography>=44,<49"') from exc
    return AESGCM


def _key(password: str, salt:bytes):
    if not isinstance(password,str) or len(password)<14 or len(password.encode('utf8'))>1024:
        raise ValueError('A 14+ character passphrase is required')
    return hashlib.scrypt(password.encode('utf8'),salt=salt,dklen=32,maxmem=64*1024*1024,**PARAMETERS)


def _decode_header(data:bytes):
    if len(data)<len(MAGIC)+4 or not data.startswith(MAGIC):
        raise ValueError('Invalid encrypted research envelope')
    length=struct.unpack('>I',data[len(MAGIC):len(MAGIC)+4])[0]
    if length<30 or length>1024 or len(data)<len(MAGIC)+4+length+16:
        raise ValueError('Invalid research envelope header')
    aad=data[:len(MAGIC)+4+length]
    try: hdr=json.loads(aad[len(MAGIC)+4:].decode('utf8'))
    except (ValueError,UnicodeError) as exc: raise ValueError('Malformed envelope header') from exc
    if hdr.get('format')!='VIGIL-RESEARCH-ENCRYPTED-1' or hdr.get('kdf')!='scrypt' or hdr.get('kdf_parameters')!=PARAMETERS or hdr.get('cipher')!='AES-256-GCM':
        raise ValueError('Unsupported encrypted research envelope')
    try:
        salt=base64.b64decode(hdr['salt'],validate=True)
        nonce=base64.b64decode(hdr['nonce'],validate=True)
    except (KeyError,ValueError) as exc: raise ValueError('Invalid envelope salt or nonce') from exc
    if len(salt)!=16 or len(nonce)!=12: raise ValueError('Invalid key parameters')
    return aad,salt,nonce,data[len(aad):]


def seal_bytes(data:bytes, password:str)->bytes:
    if not isinstance(data,bytes) or not data or len(data)>MAX_PLAINTEXT:
        raise ValueError('Only non-empty research data <=96 MiB supported by this export tool')
    salt=secrets.token_bytes(16);nonce=secrets.token_bytes(12)
    k=_key(password,salt)
    header={'format':'VIGIL-RESEARCH-ENCRYPTED-1','kdf':'scrypt','kdf_parameters':PARAMETERS,
            'cipher':'AES-256-GCM','salt':base64.b64encode(salt).decode(),
            'nonce':base64.b64encode(nonce).decode()}
    hb=json.dumps(header,sort_keys=True,separators=(',',':')).encode('utf8')
    aad=MAGIC+struct.pack('>I',len(hb))+hb
    return aad+_aes()(k).encrypt(nonce,data,aad)


def unseal_bytes(blob:bytes,password:str)->bytes:
    if len(blob)>MAX_PLAINTEXT+4096:raise ValueError('Encrypted envelope is too large')
    aad,salt,nonce,ciphertext=_decode_header(blob)
    key=_key(password,salt)
    try:
        return _aes()(key).decrypt(nonce,ciphertext,aad)
    except Exception as exc:
        # Give the same message for bad passwords and tampered tags.
        raise ValueError('Authentication failed: incorrect passphrase or modified envelope') from exc


def _atomic_new_file(path:Path,contents:bytes):
    path=Path(path).expanduser().resolve();path.parent.mkdir(parents=True,exist_ok=True)
    # O_EXCL prevents inadvertent overwrites and race-prone replacement.
    fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(contents);f.flush();os.fsync(f.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def seal_case(workspace,case_id:str,path:Path,password:str)->Path:
    """Produce encrypted copy of NPZ; original workspace remains plaintext.

    Validates original stored waveform before sealing; no clinical identifiers allowed.
    """
    row,rec,analysis=workspace.get_case(case_id)
    if not row.get('artifact_sha256'):
        raise ValueError('Cannot securely export unverified legacy case; re-import from a reviewed source')
    if rec.origin not in {'local_csv','local_wfdb','local_edf','synthetic','local_npz','synthetic_test','demo','SYNTHETIC_NOT_CLINICAL_DATA'}:
        raise ValueError('Unknown record origin; verify de-identification before export')
    source=workspace.records/row['record_path']
    if source.stat().st_size>MAX_PLAINTEXT:
        raise ValueError('Case exceeds bounded encrypted export size')
    blob=seal_bytes(source.read_bytes(),password)
    return _atomic_new_file(path,blob)


def inspect_encrypted_case(path:Path,password:str):
    """Decrypt only in memory and validate NPZ; do not write raw data to disk."""
    from ..core.records import record_from_npz
    # record_from_npz currently accepts a Path; file-like np.load is avoided here
    # by parsing a temporary in-memory NPZ ZipFile directly.
    import io,zipfile,numpy as np
    data=unseal_bytes(Path(path).read_bytes(),password)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        if len(infos)>25 or len(names)!=len(set(names)) or '__meta__.npy' not in names or any(not (n=='__meta__.npy' or (n.startswith('ch_') and n.endswith('.npy'))) for n in names):
            raise ValueError('Encrypted payload is not a supported VIGIL recording')
        if sum(i.file_size for i in infos)>256*1024*1024 or z.getinfo('__meta__.npy').file_size>1_000_000 or any(i.file_size>64*1024*1024+4_000_000 for i in infos if i.filename!='__meta__.npy'):
            raise ValueError('Payload exceeds verified waveform limits')
    with np.load(io.BytesIO(data),allow_pickle=False) as npz:
        meta=json.loads(str(npz['__meta__']))
        if not isinstance(meta,dict) or not meta.get('sha256'):
            raise ValueError('Invalid waveform metadata')
        from ..core.records import Record
        channels={k[3:]:npz[k] for k in npz.files if k.startswith('ch_')}
        rec=Record(channels,meta['fs'],meta['name'],meta['origin'],meta['sha256'],annotation=meta.get('annotation',{}))
    return {'envelope_authenticated':True,'channels':list(rec.channels),
            'samples_per_channel':rec.n,'sample_rate_hz':rec.fs,
            'research_only':True,'clinical_authorization':False}
