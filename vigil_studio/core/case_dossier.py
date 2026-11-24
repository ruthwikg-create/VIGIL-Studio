"""Publication-style, research-only VIGIL Studio case dossier.

Visual architecture is intentionally separate from analysis. This module only
reports measurements already present in the supplied analysis and waveform.
Nothing in these documents constitutes clinical validation or clearance.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import math
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

PAPER_W, PAPER_H = A4
INK = colors.HexColor('#213133')
COPPER = colors.HexColor('#CE6746')
TEAL = colors.HexColor('#147D80')
SAND = colors.HexColor('#F6F7F3')
LINE = colors.HexColor('#D8E1DC')
FADED = colors.HexColor('#586F70')
WHITE = colors.white
DANGER = colors.HexColor('#A94C45')
CHANNEL_COLORS = {'ECG':'#B75039','PPG':'#178789','ABP':'#5861A4',
                  'RESP':'#AC8043','EEG':'#7F5D9C','EMG':'#477F57'}
LM = 18*mm
CW = PAPER_W - 2*LM


def _fmt(x, digits=3):
    try:
        f=float(x)
        if not math.isfinite(f): return 'Not available'
        return f'{f:,.{digits}f}'
    except (TypeError,ValueError):return 'Not measured'


def _x(x, maxlen=500):
    t=str(x if x is not None else 'Not available')
    if len(t)>maxlen:t=t[:maxlen]+'...'
    return escape(t.replace('\x00',''))


def _styles():
    return {k:ParagraphStyle('case_'+k,**v) for k,v in {
        'eyebrow':dict(fontName='Helvetica-Bold',fontSize=8.2,leading=11,textColor=COPPER,spaceAfter=6),
        'h1':dict(fontName='Helvetica-Bold',fontSize=24,leading=29,textColor=INK,spaceAfter=8),
        'h2':dict(fontName='Helvetica-Bold',fontSize=13,leading=17,textColor=INK,spaceBefore=9,spaceAfter=8),
        'h3':dict(fontName='Helvetica-Bold',fontSize=10,leading=14,textColor=INK,spaceBefore=7,spaceAfter=5),
        'sub':dict(fontName='Helvetica',fontSize=10,leading=15,textColor=FADED,spaceAfter=13),
        'p':dict(fontName='Helvetica',fontSize=9,leading=14,textColor=INK,spaceAfter=7),
        'note':dict(fontName='Helvetica',fontSize=8.2,leading=12,textColor=FADED,spaceAfter=5),
        'tiny':dict(fontName='Helvetica',fontSize=7.1,leading=10,textColor=FADED),
        'th':dict(fontName='Helvetica-Bold',fontSize=8,leading=10.5,textColor=WHITE),
        'td':dict(fontName='Helvetica',fontSize=8.1,leading=11.2,textColor=INK),
        'metric_label':dict(fontName='Helvetica-Bold',fontSize=7.6,leading=10,textColor=FADED,alignment=TA_CENTER),
        'metric':dict(fontName='Helvetica-Bold',fontSize=18,leading=23,textColor=INK,alignment=TA_CENTER),
        'metric_note':dict(fontName='Helvetica',fontSize=7,leading=9,textColor=FADED,alignment=TA_CENTER),
        'badge':dict(fontName='Helvetica-Bold',fontSize=8.2,leading=12,textColor=DANGER),
    }.items()}


def _table(rows, widths, s, head=True):
    content=[]
    for i,row in enumerate(rows):
        style=s['th'] if i==0 and head else s['td']
        content.append([Paragraph(_x(cell,240),style) for cell in row])
    t=Table(content,colWidths=widths,repeatRows=1 if head else 0,hAlign='LEFT')
    commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),
              ('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),
              ('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.4,LINE)]
    if head:
        commands += [('BACKGROUND',(0,0),(-1,0),INK),('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,SAND])]
    else:
        commands += [('ROWBACKGROUNDS',(0,0),(-1,-1),[SAND,WHITE])]
    t.setStyle(TableStyle(commands))
    return t


def _para(s,text,style='p'):
    return Paragraph(_x(text,1400),s[style])


def _figure_image(fig,width_mm=172):
    b=io.BytesIO()
    FigureCanvasAgg(fig).print_png(b)
    b.seek(0)
    w=width_mm*mm
    return Image(b,width=w,height=w*fig.get_figheight()/fig.get_figwidth())


def _type(label):
    s=''.join(ch for ch in label.upper() if ch.isalnum())
    if s.startswith('ECG') or s in ('MLII','II','V5','V1','V2','V3','V4','V6'):return 'ECG'
    if 'PPG' in s or 'PLETH' in s:return 'PPG'
    if s in ('ABP','ART','BP'):return 'ABP'
    if 'RESP' in s:return 'RESP'
    if s.startswith('EEG'):return 'EEG'
    if s.startswith('EMG'):return 'EMG'
    return 'OTHER'


def _color(name):return CHANNEL_COLORS.get(_type(name),'#268D91')


def _wave_fig(rec, duration=15):
    chans=list(rec.channels.items())
    # More than eight channels are plotted on the first two figure pages in
    # future workflows; this report deliberately states the preview limit.
    plotted=chans[:6]
    n=min(rec.n,max(1,int(rec.fs*duration)))
    fig=Figure(figsize=(9.0,1.7*len(plotted)+.72),dpi=140,facecolor='#FFFFFF')
    axes=np.atleast_1d(fig.subplots(len(plotted),1,sharex=True))
    for ax,(name,x) in zip(axes,plotted):
        step=max(1,int(math.ceil(n/2700)))
        tt=np.arange(0,n,step)/rec.fs
        ax.plot(tt,np.asarray(x)[:n:step],color=_color(name),linewidth=1.0,rasterized=True)
        ax.set_ylabel(name[:13],fontsize=8,color='#213133',rotation=0,labelpad=23,va='center')
        ax.grid(alpha=.46,color='#DDE6E2',linewidth=.5)
        ax.spines[['top','right','left']].set_visible(False)
        ax.spines['bottom'].set_color('#B6C5BF')
        ax.tick_params(colors='#657675',labelsize=7.4,length=0)
        ax.set_facecolor('#FFFFFF')
        ax.set_xlim(0,n/rec.fs)
    axes[-1].set_xlabel('ELAPSED TIME  /  seconds',fontsize=8.2,color='#485E60')
    fig.subplots_adjust(left=.14,right=.98,top=.99,bottom=.10,hspace=.25)
    return fig


def _trend_fig(analysis, duration):
    fig=Figure(figsize=(9.0,5.8),dpi=140,facecolor='#FFFFFF')
    ax=fig.add_subplot(111)
    valid=False
    for name,data in analysis.get('channels',{}).items():
        windows=data.get('windows') or []
        pts=[(r.get('start_s'),r.get('quality_score')) for r in windows if r.get('start_s') is not None and r.get('quality_score') is not None]
        if not pts:continue
        valid=True
        xx,yy=zip(*pts)
        ax.plot(xx,yy,label=name[:20],color=_color(name),linewidth=1.6)
    ax.set_ylim(-.03,1.05);ax.set_xlim(0,max(.1,duration))
    ax.grid(color='#DEE6E1',linewidth=.6)
    ax.spines[['top','right']].set_visible(False)
    ax.tick_params(labelsize=8,colors='#617371')
    ax.set_xlabel('WINDOW START  /  seconds',fontsize=8.5)
    ax.set_ylabel('EXPLORATORY INDEX',fontsize=8.5)
    if valid:ax.legend(fontsize=8,ncol=min(4,len(analysis.get('channels',{}))),frameon=False,loc='lower left')
    fig.subplots_adjust(left=.09,right=.98,bottom=.19,top=.96)
    return fig


def _metrics(s, values):
    cells=[]
    for name,value,unit in values:
        cells.append([Paragraph(_x(name).upper(),s['metric_label']),
                      Paragraph(_x(value),s['metric']),Paragraph(_x(unit),s['metric_note'])])
    widths=[CW/len(cells)]*len(cells)
    t=Table([[Table([[v] for v in cell],colWidths=[widths[i]-9*mm],style=TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),SAND),('TOPPADDING',(0,0),(-1,0),10),
        ('BOTTOMPADDING',(0,-1),(-1,-1),10),('LEFTPADDING',(0,0),(-1,-1),0),
        ('RIGHTPADDING',(0,0),(-1,-1),0)])) for i,cell in enumerate(cells)]],colWidths=widths)
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),
                           ('RIGHTPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    return t


def create_case_pdf(rec, analysis, reviews, destination, plot_png=None):
    """Create a consistent, multi-page engineering report. plot_png is accepted
    for v4.x API compatibility; a standardized raw-data preview is generated.
    """
    path=Path(destination)
    path.parent.mkdir(parents=True,exist_ok=True)
    styles=_styles()
    report_id=f'VS-{str(rec.sha256)[:12].upper()}'
    timestamp=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    story=[]
    logo=Path(__file__).resolve().parents[1]/'assets'/'vigil_signal_icon.png'
    def sheet(canvas,doc):
        canvas.saveState()
        canvas.setFillColor(INK);canvas.rect(0,PAPER_H-13*mm,PAPER_W,13*mm,stroke=0,fill=1)
        if logo.is_file():
            canvas.drawImage(str(logo),LM,PAPER_H-10.7*mm,width=8*mm,height=8*mm,preserveAspectRatio=True,mask='auto')
        canvas.setFillColor(WHITE);canvas.setFont('Helvetica-Bold',8.2)
        canvas.drawString(LM+10*mm,PAPER_H-8.1*mm,'VIGIL STUDIO   /   INSTRUMENT WORKBENCH')
        canvas.setFillColor(COPPER);canvas.rect(PAPER_W-LM-26*mm,PAPER_H-13*mm,26*mm,13*mm,stroke=0,fill=1)
        canvas.setFillColor(WHITE);canvas.setFont('Helvetica-Bold',7.3)
        canvas.drawCentredString(PAPER_W-LM-13*mm,PAPER_H-8.2*mm,'RESEARCH')
        canvas.setStrokeColor(LINE);canvas.line(LM,17*mm,PAPER_W-LM,17*mm)
        canvas.setFont('Helvetica',7);canvas.setFillColor(FADED)
        canvas.drawString(LM,11.7*mm,report_id+'  |  NOT FOR CLINICAL DECISIONS')
        canvas.drawRightString(PAPER_W-LM,11.7*mm,f'{doc.page:02d}  /  VIGIL')
        canvas.restoreState()
    doc=BaseDocTemplate(str(path),pagesize=A4,leftMargin=LM,rightMargin=LM,
                        topMargin=23*mm,bottomMargin=23*mm,
                        title=f'VIGIL Studio - Research Case Report - {rec.name}',
                        author='VIGIL Studio | Developed By Ruthwik Goparaju',
                        subject='Unvalidated biomedical research data analysis')
    frame=Frame(LM,21*mm,CW,PAPER_H-45*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id='technical',frames=frame,onPage=sheet))

    # PAGE 1: executive dossier + traceability
    story.append(_para(styles,'ENGINEERING REPORT  /  RESEARCH RECORD','eyebrow'))
    story.append(_para(styles,'Physiological signal analysis','h1'))
    story.append(_para(styles,'A structured, reproducible summary of imported waveforms, descriptive quality indices and the limits of the current research algorithms.','sub'))
    story.append(_metrics(styles,[('Channels',str(len(rec.channels)),'imported channels'),
                                  ('Sample rate',_fmt(rec.fs,0)+' Hz','recorded sampling'),
                                  ('Duration',_fmt(rec.duration,1)+' s','full recording'),
                                  ('Review records',str(len(reviews or [])),'human reviews')]))
    story.append(Spacer(1,7*mm))
    story.append(_para(styles,'USE RESTRICTION  /  UNVALIDATED SOFTWARE','badge'))
    story.append(_para(styles,'This document contains research-only measurements and synthetic or external study data. It is not a diagnostic report, device alarm assessment, or authorization for patient management.','p'))
    story.append(_para(styles,'01   Recording provenance','h2'))
    rows=[['Field','Recorded value'],['Recording',rec.name],['Origin',rec.origin],
          ['Source SHA-256',rec.sha256],['Analysis engine',analysis.get('engine','Not recorded')],
          ['Analysis status',analysis.get('overall','Not recorded')],
          ['Generated (UTC)',timestamp],['Document identifier',report_id]]
    story.append(_table(rows,[38*mm,CW-38*mm],styles))
    story.append(_para(styles,'02   Channel-level evidence','h2'))
    rows=[['Channel','Class','Index*','Available','Rate (bpm)','Flags']]
    for name,d in analysis.get('channels',{}).items():
        q=d.get('quality') or {}; rate=d.get('rate') or {}
        av=q.get('availability')
        rows.append([name,d.get('kind','OTHER'),_fmt(q.get('quality_score')),f'{100*float(av):.1f}%' if av is not None else 'N/A',
                     _fmt(rate.get('estimated_bpm'),1) if rate.get('estimated_bpm') is not None else 'Not measured',
                     ', '.join(q.get('flags') or []) or 'None'])
    story.append(_table(rows,[30*mm,21*mm,20*mm,27*mm,28*mm,CW-126*mm],styles))
    story.append(Spacer(1,3*mm))
    story.append(_para(styles,'* Indices are uncalibrated software heuristics and are not clinical probabilities or accuracy scores. A stable index cannot rule out arrhythmia or sensor error.','note'))

    # PAGE 2: standardized waveform view
    story.append(PageBreak())
    story.append(_para(styles,'SIGNAL EVIDENCE  /  VISUAL INSPECTION','eyebrow'))
    story.append(_para(styles,'Multi-channel waveform review','h1'))
    n_plotted=min(6,len(rec.channels));duration=min(15,rec.duration)
    story.append(_para(styles,f'Raw trace preview: first {_fmt(duration,1)} seconds. Showing {n_plotted} of {len(rec.channels)} channels. Signal amplitude is in source-native units; calibration is not independently verified.','sub'))
    story.append(_figure_image(_wave_fig(rec,duration),172))
    story.append(Spacer(1,3*mm))
    story.append(_para(styles,'Figure 1. Waveform rendering is descriptive only; it is not a diagnosis, event adjudication or independently validated detector result. Display traces are downsampled when necessary.','note'))
    story.append(_para(styles,'Scope of this figure','h2'))
    for text in ['Unfiltered source recordings are shown to preserve visible signal morphology.',
                 'Only an early excerpt is shown; later artifacts and rare events may be absent.',
                 'Channels can originate from different modalities and may not have directly comparable amplitude scales.']:
        story.append(_para(styles,'- '+text,'note'))

    # PAGE 3: trend + window-level metrics
    story.append(PageBreak())
    story.append(_para(styles,'SIGNAL EVIDENCE  /  QUALITY WINDOWS','eyebrow'))
    story.append(_para(styles,'Window-by-window quality review','h1'))
    story.append(_para(styles,'Exploratory quality indices across the complete recording. Trends help locate segments for independent review; scores are not calibrated to clinical error risk.','sub'))
    story.append(_figure_image(_trend_fig(analysis,rec.duration),172))
    story.append(Spacer(1,2*mm))
    story.append(_para(styles,'Figure 2. Window positions use the analysis output timestamps and the current unvalidated quality score. No label implies clinical sensitivity or specificity.','note'))
    story.append(_para(styles,'03   Segment-level evidence inventory','h2'))
    rows=[['Channel','Windows','Min index','Median index','Max index','Flagged']]
    for name,d in analysis.get('channels',{}).items():
        windows=d.get('windows') or []
        vals=[float(v['quality_score']) for v in windows if v.get('quality_score') is not None and math.isfinite(float(v['quality_score']))]
        flagged=sum(bool(v.get('flags')) for v in windows)
        rows.append([name,str(len(windows)),_fmt(min(vals) if vals else None),
                     _fmt(float(np.median(vals)) if vals else None),_fmt(max(vals) if vals else None),str(flagged)])
    story.append(_table(rows,[30*mm,24*mm,29*mm,34*mm,29*mm,CW-146*mm],styles))
    story.append(Spacer(1,3*mm))
    story.append(_para(styles,'The number of flagged windows is determined by the software heuristics, not an expert-defined artifact ground truth. Flagged windows may overlap.','note'))

    # PAGE 4: evidence boundary + reviewer info
    story.append(PageBreak())
    story.append(_para(styles,'DATA GOVERNANCE  /  REVIEW & LIMITATIONS','eyebrow'))
    story.append(_para(styles,'Review, limitations & sign-off','h1'))
    story.append(_para(styles,'A clear account of annotation provenance and what can reasonably be concluded from the current analysis.','sub'))
    story.append(_para(styles,'04   Human review history','h2'))
    if not reviews:
        story.append(_para(styles,'No human reviews were recorded for this case at the time of export. No reviewer sign-off or clinical adjudication is implied.','p'))
    else:
        rv=[['Timestamp','Label','Reviewer / note']]
        for r in list(reviews)[:30]:
            rv.append([str(r.get('created') or r.get('created_utc') or 'Not recorded')[:24],
                       r.get('label','Not recorded'),
                       f"{r.get('reviewer') or r.get('author') or 'Unspecified'}: {str(r.get('note') or '')[:120]}"])
        story.append(_table(rv,[42*mm,41*mm,CW-83*mm],styles))
        if len(reviews)>30:story.append(_para(styles,f'{len(reviews)-30} additional review entries omitted from the print layout; retrieve them from authorized machine-readable exports.','note'))
    story.append(_para(styles,'05   Interpretation constraints','h2'))
    for item in analysis.get('limitations',[]):
        story.append(_para(styles,'- '+str(item),'p'))
    story.append(_para(styles,'06   Reproducibility and evidence scope','h2'))
    story.append(_table([['Evidence item','Status'],
         ['Source waveform',f'SHA-256: {rec.sha256}'],
         ['Calculation provenance',analysis.get('engine','Not recorded')],
         ['Raw waveform embedded in PDF','No: only rendered descriptive traces'],
         ['Ground-truth clinical labels','Not established by this report'],
         ['Clinical release authorization','NOT ESTABLISHED']],
         [49*mm,CW-49*mm],styles))
    story.append(Spacer(1,4*mm))
    story.append(_para(styles,'Document control','h2'))
    story.append(_para(styles,f'{report_id}  |  Issued {timestamp}  |  VIGIL Studio Instrument Workbench. Developed By Ruthwik Goparaju. Research evidence only.','note'))
    doc.build(story)
    return path
