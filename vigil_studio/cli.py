"""Reproducible offline research command-line interface."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .core.importers import open_record
from .core.processing import analyze_record
from .core.store import Workspace
from .core.modeling import train_experiment,save_model
from .core.reporting import export_window_csv,pdf_report


def main(argv=None):
    p=argparse.ArgumentParser(description='VIGIL Studio — research ONLY, no medical use')
    p.add_argument('--workspace',default=str(Path.home()/'VIGILStudio_Workspace'))
    sub=p.add_subparsers(dest='cmd',required=True)
    imp=sub.add_parser('import',help='Import and analyze a waveform to local workspace')
    imp.add_argument('file');imp.add_argument('--fs',type=float,help='Required for CSV without time column')
    imp.add_argument('--max-seconds',type=float,default=300)
    imp.add_argument('--windows-out',help='CSV output of time-window features')
    train=sub.add_parser('train',help='Train a RESEARCH quality classifier from independently labelled CSV')
    train.add_argument('labels_csv');train.add_argument('--model-out',required=True)
    sub.add_parser('cases');sub.add_parser('audit')
    report=sub.add_parser('report');report.add_argument('case_id');report.add_argument('--out',required=True)
    args=p.parse_args(argv);w=Workspace(args.workspace)
    try:
        if args.cmd=='import':
            rec=open_record(Path(args.file),args.fs,args.max_seconds)
            analysis=analyze_record(rec)
            id=w.add_case(rec,analysis)
            if args.windows_out:export_window_csv(analysis,args.windows_out)
            print(json.dumps({'case_id':id,'name':rec.name,'summary':analysis['overall'],'channels':list(rec.channels),'research_only':True},indent=2))
        elif args.cmd=='train':
            result,model=train_experiment(args.labels_csv);save_model(model,args.model_out)
            id=w.add_experiment('quality_experiment',{'labels_csv':Path(args.labels_csv).name},result)
            print(json.dumps({'experiment_id':id,'metrics':result,'model':args.model_out},indent=2))
        elif args.cmd=='cases':
            print(json.dumps([{k:v for k,v in c.items() if k!='metadata_json'} for c in w.list_cases()],indent=2))
        elif args.cmd=='audit':print(json.dumps(w.verify_audit(),indent=2))
        elif args.cmd=='report':
            _,rec,analysis=w.get_case(args.case_id);pdf_report(rec,analysis,w.reviews(args.case_id),args.out)
            print(str(Path(args.out).resolve()))
        return 0
    except Exception as exc:
        print('ERROR:',str(exc),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
