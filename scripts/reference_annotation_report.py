"""Create a styled research-reference inventory from a WFDB annotation CSV.

This report counts published reference symbols only; it makes NO automated
arrhythmia prediction, ECG classification, or clinical performance claim.
"""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from vigil_studio.core.professional_reports import write_reference_summary_pdf

def main(argv=None):
    p=argparse.ArgumentParser(description='Professional reference-label report, not model performance')
    p.add_argument('annotation_csv',type=Path,help='CSV generated from original .atr references')
    p.add_argument('--record',default='MIT-BIH Record 100',help='Reference source label')
    p.add_argument('--fs',type=float,default=360,help='Recording nominal sample frequency (Hz)')
    p.add_argument('--out',type=Path,help='New PDF filename; existing PDFs are never overwritten')
    a=p.parse_args(argv)
    destination=a.out if a.out else a.annotation_csv.with_name(a.annotation_csv.stem+'_Reference_Review.pdf')
    try:
        if not a.annotation_csv.is_file():raise FileNotFoundError('Annotation CSV was not found')
        if destination.exists():raise FileExistsError('Refusing to overwrite existing PDF')
        if a.fs<=0:raise ValueError('Sampling frequency must be positive')
        write_reference_summary_pdf(a.annotation_csv,destination,source_label=a.record,sample_rate=a.fs)
        print('Saved professional reference-annotation PDF:',destination.resolve())
        print('Reference labels only. This is not AI diagnosis, clinical evaluation or medical clearance.')
        return 0
    except Exception as exc:
        print(f'REPORT ERROR: {type(exc).__name__}: {exc}',file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
