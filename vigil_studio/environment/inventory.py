"""Fast metadata-only WFDB indexing and local workspace size inventory.

No entire multi-gigabyte waveform is loaded into memory; only `.hea` headers
are parsed and companion `.dat` existence is checked. A header is not proof
that underlying medical data is correct or clinically valid.
"""
from __future__ import annotations
import csv, datetime, hashlib, json, os, shutil
from pathlib import Path

class InventoryError(ValueError): pass

def directory_stats(root, *, max_files=2_000_000):
    root=Path(root);count=0;size=0;types={}
    if not root.is_dir():return {'exists':False,'files':0,'bytes':0,'by_extension':{}}
    for parent,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[n for n in dirs if not Path(parent,n).is_symlink()]
        for name in files:
            path=Path(parent,name)
            if path.is_symlink():continue
            count+=1
            if count>max_files:raise InventoryError('File inventory exceeds configured safety limit')
            st=path.stat();size+=st.st_size
            ext=path.suffix.lower() or '<none>'
            types[ext]=types.get(ext,0)+1
    return {'exists':True,'files':count,'bytes':size,'by_extension':dict(sorted(types.items()))}

def parse_wfdb_header(path):
    path=Path(path)
    with path.open('r',encoding='ascii',errors='replace') as inp:
        # Skip comment-only lines but do not parse clinical fields or metadata.
        first=next((line.strip() for line in inp if line.strip() and not line.startswith('#')),None)
        if not first:raise InventoryError('Empty WFDB header')
        parts=first.split()
        if len(parts)<2:raise InventoryError('Incomplete WFDB header')
        name=parts[0];channels=int(parts[1]);fs=float(parts[2].split('/')[0]) if len(parts)>2 else None
        nsamples=int(parts[3]) if len(parts)>3 and parts[3].isdigit() else None
        # WFDB multisegment headers may have no `.dat` alongside the header.
        return {'record_id':name,'channels':channels,'fs_hz':fs,'samples':nsamples,
                'duration_s':round(nsamples/fs,3) if nsamples is not None and fs and fs>0 else None,
                'dat_present':path.with_suffix('.dat').is_file(),
                'header_bytes':path.stat().st_size}

def build_wfdb_index(dataset_dir,output,max_records=500_000):
    dataset_dir=Path(dataset_dir).resolve();output=Path(output).resolve()
    if not dataset_dir.is_dir():raise InventoryError('Dataset directory does not exist')
    if output.is_relative_to(dataset_dir):raise InventoryError('Write the index outside the original dataset directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    tmp=output.with_name(output.name+'.partial');counter=0;invalid=0;problems=[]
    # Deterministic order is important for comparisons across installs.
    with tmp.open('w',encoding='utf-8',newline='') as dst:
        for path in sorted(dataset_dir.rglob('*.hea')):
            if path.is_symlink():continue
            counter+=1
            if counter>max_records:raise InventoryError('Dataset contains more WFDB headers than allowed')
            try:
                info=parse_wfdb_header(path)
                info['relative_path']=path.relative_to(dataset_dir).as_posix()
                info['header_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                dst.write(json.dumps(info,allow_nan=False)+'\n')
            except (OSError,ValueError,OverflowError) as exc:
                invalid+=1
                if len(problems)<20:problems.append({'relative_path':path.relative_to(dataset_dir).as_posix(),'issue':str(exc)[:180]})
        dst.flush();os.fsync(dst.fileno())
    tmp.replace(output)
    result={'dataset_dir':str(dataset_dir),'output':str(output),
            'record_headers':counter,'invalid_headers':invalid,'sample_failures':problems,
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'valid_annotated_ground_truth':False}
    output.with_suffix(output.suffix+'.summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

def resource_status(workspace):
    workspace=Path(workspace);workspace.mkdir(parents=True,exist_ok=True)
    usage=shutil.disk_usage(workspace)
    import platform,os
    result={'platform':platform.system(),'python':platform.python_version(),
            'logical_cpu_cores':os.cpu_count(),'disk_free_gb':round(usage.free/1e9,2),
            'disk_total_gb':round(usage.total/1e9,2)}
    try:
        import psutil
        result['memory_total_gb']=round(psutil.virtual_memory().total/1e9,2)
        result['memory_available_gb']=round(psutil.virtual_memory().available/1e9,2)
    except ImportError:result['memory']='Install psutil for memory information'
    # GPU probing is intentionally left as an explicit command so a normal UI
    # startup never initializes CUDA or pulls in the costly torch runtime.
    return result

def verify_publisher_sha256s(dataset_dir,*,max_entries=500_000,max_bytes=100_000_000_000):
    """Opt-in hash comparison to a dataset's INCLUDED `SHA256SUMS.txt`.

    Only validates manifest entries that can be securely resolved inside the
    dataset. Full verification may read many GB. A source-supplied checksum
    file without an independently authenticated signature remains distinct
    from cryptographic proof of publisher identity.
    """
    import re
    root=Path(dataset_dir).resolve()
    if not root.is_dir():raise InventoryError('Dataset is not installed')
    matches=list(root.rglob('SHA256SUMS.txt'))
    if not matches:
        return {'status':'NO_PUBLISHER_CHECKSUM_LIST','checked':0,'matched':0,'missing':0,'mismatched':0}
    if len(matches)>10:raise InventoryError('Unexpected number of checksum manifests')
    checked=matched=missing=mismatched=bytes_hashed=0
    problems=[];unparsed=0
    for sums in matches:
        with sums.open('r',encoding='utf-8',errors='replace') as text_file:
            for line in text_file:
                if not line.strip():continue
                item=re.match(r'^([0-9a-fA-F]{64})\s+\*?(.*?)\s*$',line)
                if not item:
                    unparsed+=1;continue
                digest,filename=item.groups()
                if not filename:unparsed+=1;continue
                target=(sums.parent/filename).resolve()
                if not target.is_relative_to(root) or target.is_symlink():
                    raise InventoryError('Checksum manifest contains path outside dataset')
                checked+=1
                if checked>max_entries:raise InventoryError('Checksum manifest too large')
                if not target.is_file():
                    missing+=1
                    if len(problems)<20:problems.append({'file':filename,'issue':'missing'})
                    continue
                bytes_hashed+=target.stat().st_size
                if bytes_hashed>max_bytes:raise InventoryError('Too much data requested for verification')
                actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.stat().st_size<16*1024*1024 else _stream_sha256(target)
                if actual.lower()==digest.lower():matched+=1
                else:
                    mismatched+=1
                    if len(problems)<20:problems.append({'file':filename,'issue':'SHA256 mismatch'})
    state='PASS_MATCHED_ENTRIES' if checked and not (missing or mismatched or unparsed) else 'INCOMPLETE_OR_FAILED'
    return {'status':state,'checked':checked,'matched':matched,'missing':missing,
            'mismatched':mismatched,'unparsed_lines':unparsed,
            'bytes_hashed':bytes_hashed,'problems':problems,
            'source_integrity_caveat':'The manifest is shipped with source files, not independently signed'}

def _stream_sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for data in iter(lambda:f.read(4*1024*1024),b''):h.update(data)
    return h.hexdigest()
