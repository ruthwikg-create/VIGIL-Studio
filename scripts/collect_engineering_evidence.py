"""Produce deterministic-scope (not deterministic-time) research engineering evidence.

No patient waveforms read. Does NOT grant certification, regulatory approval, or
clinical use; no self-attestation can do so. Writes only into a new directory.
"""
from __future__ import annotations
import argparse,hashlib,importlib.metadata,importlib.util,json,os,platform,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_DIRS=('vigil_studio','scripts','tests')
ALLOWED_ROOT=('requirements.txt','requirements-ai.txt','requirements-security.txt','requirements-build.txt','launch.py','START_WINDOWS.bat')


def sha_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest()


def source_manifest(root=ROOT):
    root=Path(root).resolve();files=[]
    for d in ALLOWED_DIRS:
        files.extend(p for p in (root/d).rglob('*.py') if p.is_file())
    files.extend(root/name for name in ALLOWED_ROOT if (root/name).is_file())
    return {str(p.relative_to(root)).replace('\\','/'):sha_file(p)
            for p in sorted(files,key=lambda x:x.as_posix())}


def dependency_inventory():
    names=('numpy','scipy','matplotlib','scikit-learn','wfdb','mne','torch','cryptography','argon2-cffi','pytest','safetensors','momentfm')
    found={}
    for name in names:
        try:found[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:found[name]='NOT_INSTALLED'
    return found


def execute_tests(root:Path,timeout_s:int=180):
    # Base installations do not have the optional PyTorch/safetensors training stack.
    # Never call a base-only run a complete AI test pass.
    optional_ai_available=all(importlib.util.find_spec(x) is not None for x in ('torch','safetensors'))
    command=[sys.executable,'-m','pytest','-q','tests']
    if not optional_ai_available:
        command.append('--ignore=tests/test_ai_research_v2.py')
    try:
        process=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                               text=True,timeout=timeout_s,check=False,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        return {'status':('PASS' if optional_ai_available else 'BASE_PASS_AI_NOT_RUN') if process.returncode==0 else 'FAIL','exit_code':process.returncode,
                'stdout':process.stdout[-40000:],'command':' '.join(command)}
    except subprocess.TimeoutExpired as exc:
        return {'status':'TIMEOUT','exit_code':None,'stdout':str(exc)[:500],'command':' '.join(command)}


def collect(output,root=ROOT,run_tests=True):
    root=Path(root).resolve()
    target=Path(output).expanduser().resolve()
    target.mkdir(parents=True,exist_ok=False)
    files=source_manifest(root)
    checks=execute_tests(root) if run_tests else {'status':'NOT_EXECUTED','exit_code':None}
    artifact={'schema':'vigil-engineering-evidence-v1',
              'utc':datetime.now(timezone.utc).isoformat(),
              'product':'VIGIL Studio 4.7 research-only',
              'clinical_use_allowed':False,
              'source_file_count':len(files),
              'source_manifest_sha256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
              'python_version':platform.python_version(),'platform':platform.platform(),
              'dependencies':dependency_inventory(),
              'test_execution':{'status':checks['status'],'exit_code':checks.get('exit_code')},
              'evidence_limitations':[
                  'Self-run automated tests do not establish analytical or clinical validity.',
                  'No external dataset or regulated clinical system was accessed.',
                  'Dependency inventory is not a verified vulnerability scan or licensed SBOM.',
                  'No authenticated clinical roles, protected live data storage or hospital integration.',
                  'Independent quality management and regulatory review have not been completed.'
              ]}
    (target/'SOURCE_SHA256.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf8')
    (target/'EVIDENCE.json').write_text(json.dumps(artifact,indent=2)+'\n',encoding='utf8')
    (target/'TEST_OUTPUT.txt').write_text(checks.get('stdout','Tests not run')+'\n',encoding='utf8')
    summary=(f'# VIGIL Studio 4.8 — local software engineering evidence\n\n'
             f'**CLINICAL USE BLOCKED — RESEARCH ONLY**\n\n'
             f'Automated tests: **{checks["status"]}** (exit {checks.get("exit_code")})\n\n'
             f'Hashed source files: **{len(files)}**\n\n'
             f'Manifest SHA-256: `{artifact["source_manifest_sha256"]}`\n\n'
             'This is a locally produced evidence snapshot, not independent verification, '
             'a signed device history record, a clinical trial, or medical-device approval.\n')
    (target/'EVIDENCE.md').write_text(summary,encoding='utf8')
    return target,artifact


def main(argv=None):
    p=argparse.ArgumentParser(description='Collect research engineering evidence; cannot authorize clinical care')
    p.add_argument('--output',required=True)
    p.add_argument('--skip-tests',action='store_true',help='Clearly marks tests NOT_EXECUTED')
    args=p.parse_args(argv)
    try:target,data=collect(args.output,run_tests=not args.skip_tests)
    except FileExistsError:
        print('Refusing to overwrite an existing evidence folder',file=sys.stderr);return 2
    print(f'Local evidence saved: {target}')
    print(f'Tests: {data["test_execution"]["status"]}')
    print('CLINICAL USE BLOCKED')
    return 0 if data['test_execution']['status'] in {'PASS','BASE_PASS_AI_NOT_RUN'} else 2
if __name__=='__main__':raise SystemExit(main())
