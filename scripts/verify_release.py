"""Verify SHA-256 hashes for all packaged files listed in RELEASE_MANIFEST.json."""
import hashlib,json,sys
from pathlib import Path

def verify(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'RELEASE_MANIFEST.json').read_text(encoding='utf8'))
    problems=[]
    for rel,digest in manifest['sha256'].items():
        p=(root/rel).resolve()
        if not p.is_relative_to(root) or not p.is_file():problems.append(rel+': missing/outside package');continue
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if actual!=digest:problems.append(rel+': hash mismatch')
    return problems, len(manifest['sha256'])

if __name__=='__main__':
    source=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
    problems,n=verify(source)
    if problems:
        print('FAILED:', '\n'.join(problems));raise SystemExit(1)
    print(f'OK: {n} files match the release manifest SHA-256.')
