"""Large research environment manager: explicit, provenance-aware installations.

Zero data/model downloads occur on import, status, catalog, plan or diagnostics.
"""
from __future__ import annotations
import argparse, json, sys, datetime
from pathlib import Path
from .catalog import BY_KEY,SOURCES,PRESETS,preset_summary
from .inventory import directory_stats,resource_status,build_wfdb_index
from .downloads import install_dataset


def report_status(workspace):
    root=Path(workspace).resolve();resources=resource_status(root)
    installed=[]
    for d in SOURCES:
        folder=root/'datasets'/d.key/d.version
        receipt=folder/'vigil_source_receipt.json'
        item={'dataset':d.key,'expected_uncompressed_gb_approx':d.unpacked_gb,'installed_receipt':receipt.is_file()}
        if item['installed_receipt']:
            try:
                obj=json.loads(receipt.read_text(encoding='utf-8'))
                item['provenance_recorded']=obj.get('dataset_id')==d.key and obj.get('version')==d.version
            except (ValueError,OSError):item['provenance_recorded']=False
            item['disk']=directory_stats(folder)
        installed.append(item)
    from ..ai.registry import model_status
    model=model_status(root)
    return {'software':'VIGIL Studio Research Environment','version':'3.0.0','workspace':str(root),
            'research_only':True,'diagnostics':resources,'datasets':installed,'foundation_model':model,
            'installed_verified_clinical_models':0,
            'notes':'Dataset receipt and archive CRC are NOT medical validity or publisher-signature verification'}


def run(argv=None):
    ap=argparse.ArgumentParser(prog='python -m vigil_studio.environment',
                               description='Local biomedical AI environment management (research only)')
    ap.add_argument('--workspace',default=str(Path.home()/'VIGILStudio_Workspace'))
    sub=ap.add_subparsers(dest='action',required=True)
    sub.add_parser('catalog',help='List exact public dataset versions, licenses and sizes')
    sub.add_parser('status',help='List local dataset, model and disk status without network')
    plan=sub.add_parser('plan',help='Explain estimated disk needs; does NOT download');plan.add_argument('--preset',choices=PRESETS,default='research-multimodal-30gb')
    install=sub.add_parser('install',help='Install one licensed public dataset from PhysioNet or a local ZIP')
    install.add_argument('dataset',choices=sorted(BY_KEY));install.add_argument('--accept-license',action='store_true')
    install.add_argument('--local-archive',help='Use an existing official ZIP file instead of downloading')
    full=sub.add_parser('install-preset',help='Explicitly install each dataset in a named research collection')
    full.add_argument('--preset',choices=PRESETS,default='research-multimodal-30gb')
    full.add_argument('--accept-licenses',action='store_true')
    full.add_argument('--continue-on-error',action='store_true')
    index=sub.add_parser('index',help='Index WFDB headers from a local installed dataset without reading samples')
    index.add_argument('dataset',choices=sorted(BY_KEY));index.add_argument('--out')
    verify=sub.add_parser('inventory',help='Compute exact local disk usage of permitted installed data')
    verify.add_argument('dataset',choices=sorted(BY_KEY))
    checks=sub.add_parser('verify-source',help='Opt-in verification of publisher-provided SHA256SUMS file')
    checks.add_argument('dataset',choices=sorted(BY_KEY))
    stress=sub.add_parser('stress-test',help='Seeded engineering perturbations on a permitted local research record')
    stress.add_argument('waveform');stress.add_argument('--fs',type=float)
    stress.add_argument('--channel',required=True);stress.add_argument('--out',required=True)
    stress.add_argument('--seconds',type=float,default=8);stress.add_argument('--seed',type=int,default=42)
    manifest=sub.add_parser('snapshot',help='Save environment provenance and installed asset status into a research JSON')
    manifest.add_argument('--out',required=True)
    args=ap.parse_args(argv);root=Path(args.workspace)
    try:
        if args.action=='catalog':result=[d.to_dict() for d in SOURCES]
        elif args.action=='status':result=report_status(root)
        elif args.action=='plan':
            from .downloads import enough_space
            result=preset_summary(args.preset)
            result['current_machine']=resource_status(root)
            result['recommended_peak_free_space_gb_for_all_downloads_approx']=45 if args.preset=='research-multimodal-30gb' else 25
            result['note']='Sizes are publisher estimates; install data one dataset at a time. Model+Python/torch extra.'
        elif args.action=='install':
            result=install_dataset(args.dataset,root,accept_license=args.accept_license,
                local_archive=args.local_archive,progress=lambda d: print('progress '+json.dumps(d),flush=True))
        elif args.action=='install-preset':
            if not args.accept_licenses:raise ValueError('Review each upstream license before passing --accept-licenses')
            result={'preset':args.preset,'results':[],'failures':[]}
            for name in PRESETS[args.preset]:
                try:
                    info=install_dataset(name,root,accept_license=True,
                        progress=lambda d: print('progress '+name+' '+json.dumps(d),flush=True))
                    result['results'].append(info)
                except Exception as exc:
                    result['failures'].append({'dataset':name,'reason':str(exc)})
                    if not args.continue_on_error:raise
            result['complete']=not result['failures']
            if result['failures']:
                print(json.dumps(result,indent=2),file=sys.stderr)
                return 2
        elif args.action=='index':
            d=BY_KEY[args.dataset];source=root/'datasets'/d.key/d.version
            result=build_wfdb_index(source,Path(args.out) if args.out else root/'indexes'/f'{d.key}-{d.version}.jsonl')
        elif args.action=='inventory':
            d=BY_KEY[args.dataset];result=directory_stats(root/'datasets'/d.key/d.version)
        elif args.action=='verify-source':
            from .inventory import verify_publisher_sha256s
            d=BY_KEY[args.dataset]
            result=verify_publisher_sha256s(root/'datasets'/d.key/d.version)
            if result['status']!='PASS_MATCHED_ENTRIES':
                print(json.dumps(result,indent=2),file=sys.stderr);return 2
        elif args.action=='stress-test':
            from ..core.importers import open_record
            from .robustness import stress_test,save_stress_report
            sample=open_record(args.waveform,fs=args.fs)
            info=stress_test(sample,args.channel,seconds=args.seconds,seed=args.seed)
            save_stress_report(info,args.out)
            result={'report':str(Path(args.out).resolve()),'cases':len(info['results']),'not_clinical_validation':True}
        elif args.action=='snapshot':
            output=Path(args.out);output.parent.mkdir(parents=True,exist_ok=True)
            result=report_status(root)
            output.write_text(json.dumps(result,indent=2,allow_nan=False,default=str),encoding='utf-8')
            result={'saved':str(output),'research_only':True}
        else:raise ValueError('Unsupported operation')
        print(json.dumps(result,indent=2,default=str,allow_nan=False))
        return 0
    except Exception as exc:
        print(f'VIGIL environment: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(run())
