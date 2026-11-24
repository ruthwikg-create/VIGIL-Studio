"""Run an independent research-only ECG peak-location benchmark on local WFDB files.

Examples (from the VIGIL Studio project folder):
  .venv\\Scripts\\python.exe scripts\\benchmark_mitbih.py D:\\Biomedical_Datasets\\MITBIH\\100.hea --channel MLII --out bench_100

This is NOT arrhythmia classification and NOT a clinical validation study.
"""
from __future__ import annotations
import argparse,sys
from pathlib import Path

# Preserve local import when invoked as a script under Windows.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vigil_studio.core.importers import read_wfdb
from vigil_studio.core.ecg_validation import evaluate_ecg_record,export_evaluation_json,export_evaluation_csv
from vigil_studio.core.processing import normalized_type


def main(argv=None):
    parser=argparse.ArgumentParser(description='VIGIL ECG research-only reference location benchmark')
    parser.add_argument('record',help='Local .hea file with matching .dat and .atr files')
    parser.add_argument('--channel',default=None,help='WFDB lead name, e.g. MLII; default first ECG lead')
    parser.add_argument('--tolerance',type=float,default=.15,help='1:1 match tolerance in seconds, default 0.15')
    parser.add_argument('--out',default='ECG_Research_Benchmark',help='Folder for JSON and CSV evaluation artifacts')
    args=parser.parse_args(argv)
    path=Path(args.record)
    if path.suffix.lower()!='.hea':parser.error('Please select the original .hea header file')
    rec=read_wfdb(path)
    valid=[n for n in rec.channels if normalized_type(n)=='ECG']
    if not valid:parser.error('No ECG lead found')
    channel=args.channel or valid[0]
    result=evaluate_ecg_record(rec,channel,args.tolerance)
    dest=Path(args.out);dest.mkdir(parents=True,exist_ok=True)
    export_evaluation_json(result,dest/'evaluation.json')
    export_evaluation_csv(result,dest/'matched_unmatched_events.csv')
    m=result['comparison']['metrics']
    print(f"Recording: {rec.name} | duration {rec.duration:.1f}s | {channel} | reference {result['reference']['n_beat_annotations']}")
    print(f"TP={m['tp']} FP={m['fp']} FN={m['fn']} Sensitivity={m['sensitivity']} PPV={m['positive_predictive_value']} F1={m['f1']}")
    print('Research-only location agreement, not arrhythmia classification or medical validation.')
    print('Saved:',dest.resolve())
    return 0

if __name__=='__main__':raise SystemExit(main())
