"""Advanced AI research CLI; all operations local except explicit model acquisition."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path

def main(argv=None):
    ap=argparse.ArgumentParser(prog='python -m vigil_studio.ai',description='VIGIL AI research-only waveform experiments')
    ap.add_argument('--workspace',default=str(Path.home()/'VIGILStudio_Workspace'))
    sub=ap.add_subparsers(dest='action',required=True)
    v=sub.add_parser('validate',help='Validate annotated waveform manifest and group splits');v.add_argument('manifest')
    t=sub.add_parser('train',help='Train group-disjoint deep learning experiment');t.add_argument('manifest');t.add_argument('--out',required=True);t.add_argument('--epochs',type=int,default=15);t.add_argument('--batch-size',type=int,default=32);t.add_argument('--seed',type=int,default=42);t.add_argument('--device',choices=['auto','cpu','cuda'],default='auto');t.add_argument('--width',type=int,default=24)
    m=sub.add_parser('model-status',help='Verify presence and SHA-256 of foundation weights')
    d=sub.add_parser('download-moment',help='Fetch official 1.39GB foundation model after explicit license acceptance');d.add_argument('--accept-license',action='store_true')
    i=sub.add_parser('infer',help='Research quality classification on a local waveform');i.add_argument('waveform');i.add_argument('--model',required=True);i.add_argument('--channel',required=True);i.add_argument('--fs',type=float);i.add_argument('--start',type=float,default=0)
    e=sub.add_parser('embed',help='Compute foundation model embeddings (requires verified weights)');e.add_argument('waveform');e.add_argument('--channel',required=True);e.add_argument('--fs',type=float);e.add_argument('--start',type=float,default=0);e.add_argument('--windows',type=int,default=8);e.add_argument('--out',required=True);e.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    args=ap.parse_args(argv)
    try:
        if args.action=='validate':
            from .datasets import load_cohort,split_by_group
            cohort=load_cohort(args.manifest);a,b,c=split_by_group(cohort.y,cohort.groups)
            result={'windows':len(cohort.y),'independent_groups':len(set(cohort.groups)),'train':len(a),'validation':len(b),'test':len(c),'split_group_overlap':0,'dataset_fingerprint':cohort.fingerprint}
        elif args.action=='train':
            from .experiment import train_model,TrainConfig
            result=train_model(args.manifest,args.out,TrainConfig(epochs=args.epochs,batch_size=args.batch_size,seed=args.seed,device=args.device,width=args.width),progress=lambda r:print(f"Epoch {r['epoch']}: loss={r['train_loss']:.4f} val balanced accuracy={r['val_balanced_accuracy_at_0_5']:.4f}",flush=True))
        elif args.action=='model-status':
            from .registry import model_status
            result=model_status(Path(args.workspace))
        elif args.action=='download-moment':
            from .registry import install_moment
            result=install_moment(Path(args.workspace),args.accept_license)
        elif args.action=='infer':
            from .experiment import predict_waveform_quality
            from ..core.importers import open_record
            result=predict_waveform_quality(open_record(Path(args.waveform),fs=args.fs),args.channel,args.model,args.start)
        elif args.action=='embed':
            import numpy as np
            from ..core.importers import open_record
            from .datasets import extract_window
            from .registry import moment_embeddings,MOMENT_ID,MOMENT_SHA256
            if not 1<=args.windows<=200:raise ValueError('windows must be 1–200')
            record=open_record(Path(args.waveform),fs=args.fs)
            times=[args.start+2*i for i in range(args.windows)]
            X=np.stack([extract_window(record,args.channel,t) for t in times]);E=moment_embeddings(X,Path(args.workspace),device=args.device)
            out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
            np.savez_compressed(out,embeddings=E,start_seconds=np.array(times,dtype=float),model_sha256=np.array(MOMENT_SHA256),model_id=np.array(MOMENT_ID),research_only=np.array(True))
            result={'embeddings_shape':list(E.shape),'out':str(out),'clinical_utility_validated':False}
        else:raise ValueError('No operation')
        print(json.dumps(result,indent=2,allow_nan=False,default=str))
    except Exception as exc:
        print(f'AI research operation failed: {exc}',file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':sys.exit(main())
