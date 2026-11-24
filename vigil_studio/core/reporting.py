"""Offline, explicitly research-labelled PDF/CSV exports."""
from pathlib import Path
import json,csv,io,datetime
import numpy as np

def safe_csv_text(value):
    """Protect spreadsheet viewers from executing formula-like content in exported text."""
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):
        return "'"+value
    return value


def export_window_csv(analysis,path):
    cols=['channel','kind','start_s','end_s','availability','flatline_fraction','high_frequency_fraction',
          'dynamic_range','quality_score','std','mad','derivative_rms','range_99_1','nonfinite_fraction','label','flags']
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for ch,v in analysis['channels'].items():
            for row in v['windows']:
                w.writerow({k:safe_csv_text(v) for k,v in {**row,'channel':ch,'flags':'|'.join(row.get('flags',[]))}.items()})
    return Path(path)

def export_waveform_csv(rec,path,start_s=0,seconds=60):
    end=min(rec.n,int((start_s+seconds)*rec.fs));start=max(0,int(start_s*rec.fs))
    if end-start>500_000:raise ValueError('Export at most 500,000 rows at a time')
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);channels=list(rec.channels)
        w.writerow(['time_s',*[safe_csv_text(ch) for ch in channels]])
        for i in range(start,end):w.writerow([i/rec.fs,*[float(rec.channels[ch][i]) for ch in channels]])

def pdf_report(rec, analysis, reviews, path, plot_png=None):
    """Generate the branded, 4-part VIGIL scientific case dossier."""
    from .case_dossier import create_case_pdf
    return create_case_pdf(rec, analysis, reviews, path, plot_png=plot_png)
