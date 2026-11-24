"""Developer reproducibility snapshot; no PHI, paths, network, or clinical authorization."""
from pathlib import Path
import argparse, hashlib, importlib.metadata as im, json, platform, sys, datetime


def snapshot():
    installed=sorted(({'name':(d.metadata['Name'] or 'unknown'), 'version':d.version}
                      for d in im.distributions()), key=lambda x:x['name'].casefold())
    return {'schema':'vigil-reproducible-environment-snapshot-v1',
            'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'python':sys.version.split()[0], 'platform':platform.platform(),
            'packages':installed, 'research_only':True, 'clinical_authorized':False,
            'note':'Informational environment inventory; version listing is not a vulnerability scan or SBOM audit.'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    output=Path(args.output).resolve()
    if output.exists():raise FileExistsError(f'Refusing overwrite: {output}')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(snapshot(),indent=2)+'\n',encoding='utf8')
    print('Environment captured:',output)

if __name__=='__main__': main()
