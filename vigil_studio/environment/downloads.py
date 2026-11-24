"""Explicit official-source downloader and safe, bounded, atomic extractor.

Only public PhysioNet datasets in the compiled catalog are eligible. Files
are never fetched automatically. User accepts the *source's* license, not
VIGIL's. SHA-256 records provenance; it does not replace publisher-signed
hashes or clinical dataset curation.
"""
from __future__ import annotations
import datetime, hashlib, json, os, shutil, stat, tempfile, urllib.error, urllib.request, zipfile
from pathlib import Path, PurePosixPath
from .catalog import BY_KEY
from .inventory import directory_stats

CHUNK=1024*1024
SAFETY_RESERVE_BYTES=1_000_000_000

class AcquisitionError(RuntimeError): pass

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(4*CHUNK),b''):
            h.update(chunk)
    return h.hexdigest()

def enough_space(destination, compressed_bytes:int, uncompressed_bytes:int):
    dest=Path(destination);dest.mkdir(parents=True,exist_ok=True)
    available=shutil.disk_usage(dest).free
    # Peak disk use while downloading and extracting, before removing archive.
    required=int(compressed_bytes+uncompressed_bytes+SAFETY_RESERVE_BYTES)
    if available<required:
        raise AcquisitionError(f'Not enough storage: {available/1e9:.2f} GB free; ' 
                               f'at least {required/1e9:.2f} GB required for the selected dataset')
    return {'free_gb':round(available/1e9,2),'peak_required_gb_approx':round(required/1e9,2)}

def _safe_member(name):
    if not name or '\\' in name or name.startswith('/') or '\0' in name or ':' in name:
        raise AcquisitionError(f'Unsafe archive entry {name!r}')
    p=PurePosixPath(name)
    if '..' in p.parts or any(part in ('','.','..') for part in p.parts):
        raise AcquisitionError(f'Path traversal archive entry {name!r}')
    return p

def inspect_zip(archive,max_files=2_000_000,max_uncompressed=20_000_000_000):
    """Parse ZIP central directory first; validate paths, sizes, file types."""
    names=set();total=0;count=0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            count+=1
            if count>max_files:raise AcquisitionError('Archive exceeds maximum entry count')
            path=_safe_member(info.filename)
            if info.flag_bits & 1:raise AcquisitionError('Encrypted archive member is unsupported')
            mode=(info.external_attr>>16)&0xFFFF
            if stat.S_ISLNK(mode):raise AcquisitionError('Symlink member is forbidden')
            normalized=path.as_posix().rstrip('/').lower()
            if normalized in names:raise AcquisitionError('Repeated archive filename (case-insensitive)')
            names.add(normalized)
            total+=info.file_size
            if total>max_uncompressed:raise AcquisitionError('Archive exceeds specified extraction size limit')
    return {'file_entries':count,'declared_unpacked_bytes':total}

def safe_extract(archive,destination,max_uncompressed=20_000_000_000):
    """Streaming extraction with ZIP CRC validation, no symlinks, overwrite or zip-slip.

    Destination must be a new/empty staging directory. Caller performs the
    atomic rename and does not consume output until extraction completes.
    """
    stats=inspect_zip(archive,max_uncompressed=max_uncompressed)
    root=Path(destination).resolve();root.mkdir(parents=True,exist_ok=True)
    if any(root.iterdir()):raise AcquisitionError('Extraction staging directory must be empty')
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            rel=_safe_member(info.filename)
            dest=root.joinpath(*rel.parts)
            if not dest.resolve().is_relative_to(root):raise AcquisitionError('Archive extraction escapes staging directory')
            if info.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as src, open(dest,'xb') as out:
                written=0
                while chunk:=src.read(CHUNK):
                    written+=len(chunk)
                    if written>info.file_size:raise AcquisitionError('Archive entry decompressed past its metadata size')
                    out.write(chunk)
                if written!=info.file_size:raise AcquisitionError('Archive entry truncated')
    return stats

def _get_url(url,existing:int,opener):
    request=urllib.request.Request(url,headers={'User-Agent':'VIGILStudioResearch/3.0 (public dataset provenance)',
                                                'Range':f'bytes={existing}-'} if existing else
                                                 {'User-Agent':'VIGILStudioResearch/3.0 (public dataset provenance)'})
    return opener(request,timeout=90)

def download_archive(url,path,expected_max_bytes,progress=None,opener=None):
    """Resumable HTTPS streaming. Range-ignore responses restart, never append incorrectly."""
    if not url.startswith('https://physionet.org/content/'):
        raise AcquisitionError('Only catalog-pinned, HTTPS PhysioNet URLs are supported')
    opener=opener or urllib.request.urlopen
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    existing=path.stat().st_size if path.is_file() else 0
    if existing>expected_max_bytes:raise AcquisitionError('Partial archive larger than maximum allowed')
    try:
        response=_get_url(url,existing,opener)
    except urllib.error.HTTPError as exc:
        if exc.code==416 and path.is_file() and existing:
            # Source might be complete already; ZIP integrity checked later.
            return {'file':str(path),'downloaded_bytes':existing,'resume_status':'ALREADY_PRESENT_UNVERIFIED'}
        raise AcquisitionError(f'Dataset server returned HTTP {exc.code}') from exc
    with response as stream:
        status=getattr(stream,'status',None) or stream.getcode()
        # Servers that ignore Range must restart, not concatenate.
        use_resume=existing>0 and status==206
        if existing and not use_resume and status!=200:
            raise AcquisitionError(f'Unexpected download HTTP status {status}')
        mode='ab' if use_resume else 'wb';running=existing if use_resume else 0
        if use_resume:
            content_range=stream.headers.get('Content-Range','')
            if not content_range.startswith(f'bytes {existing}-'):
                raise AcquisitionError('Resumed response Content-Range mismatch')
        with path.open(mode) as f:
            while chunk:=stream.read(CHUNK):
                running+=len(chunk)
                if running>expected_max_bytes:
                    raise AcquisitionError('Remote archive exceeds expected upper size limit')
                f.write(chunk)
                if progress:progress({'stage':'download','bytes':running})
            f.flush();os.fsync(f.fileno())
    if path.stat().st_size==0:raise AcquisitionError('Empty dataset download')
    return {'file':str(path),'downloaded_bytes':path.stat().st_size,'resume_status':'RESUMED' if use_resume else 'NEW'}

def install_dataset(dataset_key,workspace,*,accept_license=False,local_archive=None,progress=None):
    """Download and install one public dataset. Any network transfer is opt-in."""
    if dataset_key not in BY_KEY:raise AcquisitionError(f'Unknown dataset {dataset_key}')
    d=BY_KEY[dataset_key]
    if not accept_license:
        raise AcquisitionError(f'You must read and accept {d.license}: {d.page}')
    workspace=Path(workspace).resolve()
    folder=workspace/'datasets'/d.key/d.version
    receipt=folder/'vigil_source_receipt.json'
    if receipt.is_file():
        try:
            obj=json.loads(receipt.read_text(encoding='utf-8'))
            if obj['dataset_id']==d.key and obj['version']==d.version:
                return {'status':'ALREADY_INSTALLED','dataset':d.key,'folder':str(folder),'receipt':str(receipt)}
        except (OSError,ValueError,KeyError):pass
        raise AcquisitionError('Existing install is incomplete or has a malformed receipt; manual inspection required')
    if folder.exists():
        raise AcquisitionError('Dataset folder already exists without a valid installation receipt')
    archive_dir=workspace/'downloads';archive_dir.mkdir(parents=True,exist_ok=True)
    archive=Path(local_archive).resolve() if local_archive else archive_dir/(d.key+'-'+d.version+'.zip.partial')
    if not local_archive:
        enough_space(archive_dir,int(d.compressed_gb*1e9*1.3),int(d.unpacked_gb*1e9*1.35))
        download_archive(d.zip_url,archive,int(d.compressed_gb*1e9*1.5+300e6),progress)
    elif not archive.is_file():
        raise AcquisitionError('Explicitly supplied local dataset archive does not exist')
    allowed_unpacked=int(d.unpacked_gb*1e9*1.6+350e6)
    stats=inspect_zip(archive,max_uncompressed=allowed_unpacked)
    # Local fixture imports may be small. Still check for required extraction space.
    free=shutil.disk_usage(archive_dir).free
    if free<stats['declared_unpacked_bytes']+SAFETY_RESERVE_BYTES:
        raise AcquisitionError('Not enough free disk space to safely unpack this archive')
    folder.parent.mkdir(parents=True,exist_ok=True)
    stage=folder.parent/(folder.name+'.extracting')
    if stage.exists():
        raise AcquisitionError('Previous extraction staging folder exists: inspect or remove manually')
    stage.mkdir()
    try:
        if progress:progress({'stage':'extract','entry_count':stats['file_entries']})
        safe_extract(archive,stage,max_uncompressed=allowed_unpacked)
        checksum=sha256(archive)
        obj={'dataset_id':d.key,'name':d.name,'version':d.version,'source':d.page,
             'license':d.license,'doi':d.doi,'accepted_by_user':True,
             'installed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'archive_sha256':checksum,'archive_size':archive.stat().st_size,
             'archive_sha256_origin':'LOCAL_RECEIPT_NOT_PUBLISHER_VERIFIED',
             'uncompressed_declared_bytes':stats['declared_unpacked_bytes'],
             'research_only':True,'contains_human_research_recordings':True,
             'clinical_validated':False,'integrity':'ZIP_CRC_AND_PATH_CHECKS_ONLY'}
        (stage/'vigil_source_receipt.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')
        stage.replace(folder)
        if not local_archive:archive.unlink(missing_ok=True)
        return {'status':'INSTALLED','dataset':d.key,'folder':str(folder),
                'archive_sha256':checksum,'archive_size':obj['archive_size'],
                'declared_unpacked_bytes':stats['declared_unpacked_bytes']}
    except Exception:
        # Avoid misleading a partial result as an installed dataset.
        shutil.rmtree(stage,ignore_errors=True)
        raise
