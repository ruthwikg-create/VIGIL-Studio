"""Explicit external model provenance and verified optional acquisition.
The foundation model is never shipped or presented as already installed.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,json

MOMENT_ID='AutonLab/MOMENT-1-large'
MOMENT_BYTES=1385501256
MOMENT_SHA256='a56928052ac6f5d09b97c3834bea6ce3aef9f02b513b5fac98954e7377801572'
MOMENT_REVISION='3582f9d7f033eea9d43e6a802ba0e36d5f26b57c'

class RegistryError(RuntimeError):pass

def hash_file(path:Path,chunk=4*1024*1024)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while piece:=f.read(chunk):h.update(piece)
    return h.hexdigest()

def model_status(root:Path):
    directory=Path(root)/'models'/'moment-1-large'; weight=directory/'model.safetensors'
    result={'name':MOMENT_ID,'expected_bytes':MOMENT_BYTES,'installed':False,'path':str(directory)}
    if weight.is_file():
        result['file_bytes']=weight.stat().st_size
        if weight.stat().st_size==MOMENT_BYTES:
            result['installed']=hash_file(weight)==MOMENT_SHA256
        result['status']='VERIFIED' if result['installed'] else 'INTEGRITY_MISMATCH'
    else:result['status']='NOT_INSTALLED'
    return result

def install_moment(root:Path,accept_license:bool=False):
    if not accept_license:raise RegistryError('License review/acceptance is required before downloading model weights')
    try:from huggingface_hub import snapshot_download
    except ImportError as e: raise RegistryError('Install optional AI dependencies first: pip install -r requirements-ai.txt') from e
    directory=Path(root)/'models'/'moment-1-large';directory.mkdir(parents=True,exist_ok=True)
    if model_status(root)['installed']:return model_status(root)
    # Library downloads to a dedicated local folder. No external model code execution.
    snapshot_download(repo_id=MOMENT_ID,revision=MOMENT_REVISION,local_dir=str(directory),allow_patterns=['*.json','*.safetensors','*.md','LICENSE*'])
    status=model_status(root)
    if not status['installed']:
        raise RegistryError('Downloaded model SHA-256 or file size mismatch; refusing to use weights')
    (directory/'vigil_model_receipt.json').write_text(json.dumps({'source':MOMENT_ID,'revision':MOMENT_REVISION,'sha256':MOMENT_SHA256,'bytes':MOMENT_BYTES,'scope':'research embeddings only','clinical_validated':False},indent=2),encoding='utf-8')
    return status


def moment_embeddings(x,root:Path,batch_size:int=8,device='cpu'):
    """Encode preprocessed [windows,512] arrays using third-party MOMENT API.
    This adapter requires actual upstream model weights and momentfm installed;
    it is intentionally not reported as runtime-verified in offline CI.
    """
    import numpy as np
    import torch
    status=model_status(root)
    if not status['installed']:raise RegistryError('MOMENT-1-large must be installed and SHA-256 verified first')
    from momentfm import MOMENTPipeline
    arr=np.asarray(x,dtype=np.float32)
    if arr.ndim!=2 or arr.shape[1]!=512 or len(arr)<1 or not np.isfinite(arr).all():
        raise RegistryError('Expected finite float waveform windows of shape [N,512]')
    if batch_size<1 or batch_size>128:raise RegistryError('Batch size out of range')
    model=MOMENTPipeline.from_pretrained(status['path'],model_kwargs={'task_name':'embedding'})
    model.init();model.to(device);model.eval()
    chunks=[]
    with torch.inference_mode():
        for first in range(0,len(arr),batch_size):
            batch=torch.from_numpy(arr[first:first+batch_size,None,:]).to(device)
            mask=torch.ones((batch.shape[0],512),dtype=torch.long,device=device)
            out=model(x_enc=batch,input_mask=mask)
            vectors=out.embeddings.detach().float().cpu().numpy()
            chunks.append(vectors.reshape(len(batch),-1))
    return np.concatenate(chunks).astype('float32')
