"""Professional, factual PDF reports for offline biomedical research evidence.

All medical-use gates remain independent of engineering evidence. No benchmark,
source annotation, or report may be represented as clinical authorization.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
import csv
import hashlib
import math

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

INK = colors.HexColor('#1D2F32')
TEAL = colors.HexColor('#147E82')
COPPER = colors.HexColor('#CC6947')
MUTED = colors.HexColor('#52676A')
LIGHT = colors.HexColor('#E7EEEC')
PALE = colors.HexColor('#F6F8F6')
BLUE = colors.HexColor('#415C91')
PAGE_W, PAGE_H = A4
MARGIN = 18*mm
CONTENT_W = PAGE_W - 2*MARGIN


def _text(value, limit=400):
    s = str(value if value is not None else 'Not available').replace('\x00', '')
    return escape(s[:limit] + ('...' if len(s) > limit else ''))


def _percent(value):
    return 'Not measured' if value is None else f'{100*float(value):.2f}%'


def _num(value):
    return 'N/A' if value is None else f'{int(value):,}'


def _styles():
    base = getSampleStyleSheet()
    return {
        'eyebrow': ParagraphStyle('vig_eye', fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=TEAL, spaceAfter=9),
        'title': ParagraphStyle('vig_title', fontName='Helvetica-Bold', fontSize=23, leading=27, textColor=INK, spaceAfter=10),
        'subtitle': ParagraphStyle('vig_subtitle', fontName='Helvetica', fontSize=10, leading=15, textColor=MUTED, spaceAfter=16),
        'section': ParagraphStyle('vig_section', fontName='Helvetica-Bold', fontSize=12.5, leading=17, textColor=INK, spaceBefore=13, spaceAfter=7),
        'minor': ParagraphStyle('vig_minor', fontName='Helvetica-Bold', fontSize=9.5, leading=13, textColor=INK, spaceBefore=9, spaceAfter=5),
        'body': ParagraphStyle('vig_body', fontName='Helvetica', fontSize=8.8, leading=13.5, textColor=INK, spaceAfter=6),
        'small': ParagraphStyle('vig_small', fontName='Helvetica', fontSize=7.7, leading=11, textColor=MUTED, spaceAfter=3),
        'cell': ParagraphStyle('vig_cell', fontName='Helvetica', fontSize=7.8, leading=11, textColor=INK),
        'cellhead': ParagraphStyle('vig_cellhead', fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=colors.white),
        'note': ParagraphStyle('vig_note', fontName='Helvetica', fontSize=8.4, leading=12.8, textColor=INK),
    }


def _make_doc(path, title):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    doc=BaseDocTemplate(str(path),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,
                        topMargin=23*mm,bottomMargin=19*mm,
                        title=title,author='VIGIL Studio | Developed By Ruthwik Goparaju',
                        subject='Offline biomedical research evidence; not a medical-device approval')
    f=Frame(MARGIN,19*mm,CONTENT_W,PAGE_H-42*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
    def page(canvas,doc):
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.rect(0,PAGE_H-12*mm,PAGE_W,12*mm,fill=1,stroke=0)
        logo=Path(__file__).resolve().parents[1]/'assets'/'vigil_signal_icon.png'
        if logo.is_file():
            canvas.drawImage(str(logo),MARGIN,PAGE_H-10*mm,width=7*mm,height=7*mm,mask='auto',preserveAspectRatio=True)
        canvas.setFont('Helvetica-Bold',8.5);canvas.setFillColor(colors.white)
        canvas.drawString(MARGIN+9*mm,PAGE_H-7.8*mm,'VIGIL STUDIO  /  INSTRUMENT WORKBENCH')
        canvas.setStrokeColor(LIGHT)
        canvas.line(MARGIN,16*mm,PAGE_W-MARGIN,16*mm)
        canvas.setFillColor(MUTED);canvas.setFont('Helvetica',7)
        canvas.drawString(MARGIN,11*mm,'RESEARCH EVIDENCE  |  NOT FOR PATIENT CARE')
        canvas.drawRightString(PAGE_W-MARGIN,11*mm,f'Page {doc.page}')
        canvas.restoreState()
    doc.addPageTemplates(PageTemplate(id='main',frames=f,onPage=page))
    return doc


def _header(story, kind, title, sub, s):
    story.extend([Paragraph(_text(kind).upper(),s['eyebrow']),Paragraph(_text(title),s['title']),
                  Paragraph(_text(sub),s['subtitle'])])


def _section(story, title, s):
    story.append(Paragraph(_text(title),s['section']))


def _table(rows, widths=None, header=True, s=None):
    s=s or _styles()
    transformed=[]
    for i,row in enumerate(rows):
        transformed.append([Paragraph(_text(x,180),s['cellhead'] if i==0 and header else s['cell']) for x in row])
    widths=widths or [CONTENT_W/len(rows[0])]*len(rows[0])
    t=Table(transformed,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
    cmds=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
          ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),
          ('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.35,LIGHT)]
    if header:cmds += [('BACKGROUND',(0,0),(-1,0),INK),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE])]
    else:cmds += [('ROWBACKGROUNDS',(0,0),(-1,-1),[PALE,colors.white])]
    t.setStyle(TableStyle(cmds));return t


def _keyvalues(story, entries, s):
    story.append(_table([[k,v] for k,v in entries],widths=[47*mm, CONTENT_W-47*mm],header=False,s=s))


def _paragraph(story, text, s, style='body'):
    story.append(Paragraph(_text(text,1500),s[style]))


def _safe_figure(fig, width_mm=171):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    buf=BytesIO();FigureCanvasAgg(fig).print_png(buf);buf.seek(0)
    w=width_mm*mm
    return Image(buf,width=w,height=w*fig.get_figheight()/fig.get_figwidth())


def write_readiness_pdf(report:dict,path):
    """Render a data-backed status report; never convert self-tests into approval."""
    s=_styles();story=[]
    _header(story,'Engineering evidence / controlled release','Hospital readiness assessment',
            'A transparent account of implemented checks, open requirements, and authorization status.',s)
    check=report.get('engineering_checks') or {};status=check.get('engineering_integrity','NOT_CHECKED')
    bench=report.get('retrospective_benchmark') or {};security=report.get('security_controls') or {}
    _section(story,'Executive decision',s)
    _table_rows=[['Assessment dimension','Result'],
        ['Local engineering integrity',status],
        ['Retrospective ECG research benchmark',bench.get('status','NOT_PROVIDED')],
        ['External audit seal',security.get('external_audit_anchor',{}).get('status','NOT_CONFIGURED')],
        ['Clinical operations authorization','NOT AUTHORIZED']]
    story.append(_table(_table_rows,[77*mm,CONTENT_W-77*mm],s=s))
    story.append(Spacer(1,4*mm))
    _paragraph(story,'Engineering checks and clinical authorization are independent decisions. A passed unit test, successful checksum, or completed retrospective benchmark is not a regulatory clearance, clinical performance certification, or patient-safety approval.',s,'note')
    _section(story,'Document controls',s)
    _keyvalues(story,[('Product',report.get('product','VIGIL Studio')),
                      ('Report timestamp (UTC)',report.get('generated_utc','Not supplied')),
                      ('Authorized current use',report.get('intended_use','Offline research only')),
                      ('Document status','Engineering assessment; unsigned and not independently certified')],s)
    _section(story,'Data integrity summary',s)
    audit=check.get('audit') or {};assets=check.get('case_files') or {}
    _keyvalues(story,[('Audit chain check', 'PASS' if audit.get('valid') is True else 'NOT VERIFIED'),
                      ('Verified waveform cases',_num(assets.get('verified'))),
                      ('Failed waveform integrity cases',_num(assets.get('failed'))),
                      ('Legacy cases without verification digest',_num(assets.get('unverified_legacy'))),
                      ('Research benchmark coverage',f"{_num(bench.get('record_count'))} processed records" if bench.get('record_count') is not None else 'Not provided')],s)
    _section(story,'Security implementation boundaries',s)
    secrows=[['Protection','Current implementation']]
    mapping=[('Workspace encryption at rest','existing_workspace_encrypted_at_rest'),
             ('Hospital clinician login / role separation','hospital_staff_authentication_and_rbac'),
             ('Institutional identity provider','external_identity_provider_integrated'),
             ('Encrypted *research export* available','encrypted_research_export_available'),
             ('Independent hospital security review','hospital_security_review_complete')]
    for name,key in mapping:secrows.append([name,'Implemented (local)' if security.get(key) is True else 'Not established'])
    story.append(_table(secrows,[92*mm,CONTENT_W-92*mm],s=s))
    _section(story,'Clinical release evidence register',s)
    gates=report.get('clinical_gates') or []
    rows=[['Gate','Required work','Current evidence status']]
    for item in gates:
        rows.append([item.get('id','?'),item.get('name',''),
                     'Outstanding / independent review required' if item.get('state')=='BLOCKED' else item.get('state','UNKNOWN')])
    story.append(_table(rows,[16*mm,87*mm,CONTENT_W-103*mm],s=s))
    _section(story,'Required external actions',s)
    for item in gates:
        _paragraph(story,f"{item.get('id')}: {item.get('required_evidence')}",s,'small')
    _section(story,'Limitations and release decision',s)
    for line in [
        'The report only evaluates provided local artifacts and software-declared evidence; it does not inspect hospital infrastructure.',
        'No clinical sponsor signature, independent patient-level validation, risk acceptance, or regulatory authorization is represented as completed.',
        'Release classification: research workstation. Clinical deployment remains prohibited until independent evidence is established and reviewed.',
    ]:_paragraph(story,line,s)
    _paragraph(story,'Prepared automatically by VIGIL Studio. Requires human technical, clinical, quality, and regulatory review before use in any formal submission.',s,'small')
    _make_doc(path,'VIGIL Studio - Hospital Readiness Assessment').build(story)
    return Path(path)


def write_benchmark_pdf(run:dict,path):
    s=_styles();story=[]
    _header(story,'Retrospective study / fixed protocol','ECG beat-location benchmark',
            'Detailed research measurement of event-location agreement. Not arrhythmia classification or clinical effectiveness.',s)
    rows=run.get('records') or [];summary=run.get('summary') or {};pooled=summary.get('pooled') or {}
    check=run.get('preflight') or {};errors=run.get('errors') or []
    expected=check.get('expected_records') or []
    completed=run.get('completion_status')=='COMPLETED' and len(rows)==len(expected) and not errors
    _section(story,'Executive summary',s)
    story.append(_table([['Indicator','Measured result'],
         ['Coverage',f"{len(rows)} / {len(expected)} records; {'Complete' if completed else 'Incomplete / partial'}"],
         ['Reference event matches (TP)',_num(pooled.get('tp'))],
         ['Extra detections (FP)',_num(pooled.get('fp'))],
         ['Missed reference events (FN)',_num(pooled.get('fn'))],
         ['Sensitivity',_percent(pooled.get('sensitivity'))],
         ['Positive predictive value',_percent(pooled.get('positive_predictive_value'))],
         ['F1 score',_percent(pooled.get('f1'))],
         ['Clinical authorization','NOT AUTHORIZED']],[80*mm,CONTENT_W-80*mm],s=s))
    _section(story,'Study provenance and fixed method',s)
    protocol=run.get('protocol') or {}
    _keyvalues(story,[('Dataset','MIT-BIH Arrhythmia Database v1.0.0 (local research copy)'),
                      ('Timestamp (UTC)',run.get('created_utc','Not supplied')),
                      ('Protocol identifier',protocol.get('protocol_id','Unavailable')),
                      ('Detector',protocol.get('detector','Not stated')),
                      ('Lead selection',protocol.get('lead_rule','Not stated')),
                      ('Matching method',protocol.get('scoring','One-to-one event matching')),
                      ('Dataset completion status',run.get('completion_status','Unknown'))],s)
    _paragraph(story,'Published reference annotations are used only by the evaluator, not the peak detector. The benchmark measures temporal QRS detection, not medical diagnosis. No post-hoc detector tuning is permitted by this locked protocol.',s)
    _section(story,'Failure accounting',s)
    story.append(_table([['Issue','Count'],
                         ['Missing recording entries',str(len(check.get('missing') or []))],
                         ['Empty required recording files',str(len(check.get('empty') or []))],
                         ['Processing failures',str(len(errors))]], [95*mm,CONTENT_W-95*mm],s=s))
    if rows:
        from matplotlib.figure import Figure
        fig=Figure(figsize=(8.4,3.3),dpi=140,facecolor='white')
        ax=fig.add_subplot(111)
        sorted_rows=sorted([r for r in rows if r.get('sensitivity') is not None],
                           key=lambda r:float(r['sensitivity']))
        sample=sorted_rows[:min(len(sorted_rows),16)]
        if sample:
            vals=[100*float(r['sensitivity']) for r in sample]
            labels=[str(r.get('record_id','?')) for r in sample]
            ax.barh(labels,vals,color='#CC6947')
            ax.invert_yaxis();ax.set_xlim(0,100)
            ax.set_xlabel('Sensitivity (%) - lowest-performing records',fontsize=9)
            ax.grid(axis='x',alpha=.25);ax.set_axisbelow(True)
        fig.tight_layout()
        _section(story,'Record-level distribution',s)
        story.append(_safe_figure(fig,160))
        _paragraph(story,'The figure shows up to 16 records ranked by lowest measured sensitivity. High overall scores must not conceal poorly performing recordings.',s,'small')
        _section(story,'All completed records',s)
        d=[['Record','Lead','Ref','TP','FP','FN','Se %','PPV %']]
        for r in sorted(rows,key=lambda x:str(x.get('record_id',''))):
            p=lambda z: 'N/A' if z is None else f'{100*float(z):.1f}'
            d.append([str(r.get('record_id','')),str(r.get('lead',''))[:12],_num(r.get('n_reference_beats')),
                 _num(r.get('tp')),_num(r.get('fp')),_num(r.get('fn')),
                 p(r.get('sensitivity')),p(r.get('positive_predictive_value'))])
        story.append(_table(d,[17*mm,24*mm,18*mm,15*mm,15*mm,15*mm,23*mm,CONTENT_W-127*mm],s=s))
    if errors or check.get('missing') or check.get('empty'):
        _section(story,'Incomplete cases requiring investigation',s)
        for er in errors[:30]:_paragraph(story,f"Record {er.get('record','?')}: {er.get('error_type','Error')} - {er.get('reason','')}",s,'small')
        for item in (check.get('missing') or []):_paragraph(story,f"Missing: {item.get('record')} ({item.get('missing_files')})",s,'small')
        for item in (check.get('empty') or []):_paragraph(story,f"Empty: {item.get('record')} ({item.get('empty_files')})",s,'small')
    _section(story,'Interpretation, limitations and release status',s)
    for line in [
        'The historical MIT-BIH dataset is not a substitute for external clinical population validation.',
        'Per-record failures, false detections, and missed reference events must be reviewed individually.',
        'No clinician-approved acceptance threshold, independent prospective trial, or device-specific risk claim has been established.',
        'No diagnosis, arrhythmia classification, real-time alarm suppression, or bedside treatment guidance is validated by these metrics.',
        'Research outcome: measured engineering evidence only. Clinical operations authorization: NOT ESTABLISHED.',
    ]:_paragraph(story,line,s)
    _make_doc(path,'VIGIL Studio - ECG Retrospective Benchmark').build(story)
    return Path(path)


def write_reference_summary_pdf(annotation_csv,path,*,source_label='MIT-BIH Record 100',sample_rate=360):
    """Reference data overview from a user-supplied CSV. No invented predictions."""
    source=Path(annotation_csv)
    with source.open(newline='',encoding='utf-8') as f:
        rd=csv.DictReader(f)
        if not {'sample','time_s','symbol'}.issubset(set(rd.fieldnames or [])):
            raise ValueError('CSV missing required reference annotation columns')
        rows=[]
        for row in rd:
            sample=int(row['sample']);t=float(row['time_s'])
            if sample<0 or not math.isfinite(t) or t<0:
                raise ValueError('Invalid annotation sample/time value')
            rows.append({'sample':sample,'time_s':t,'symbol':row['symbol']})
    if not rows:raise ValueError('No reference annotations')
    counts=Counter(r['symbol'] for r in rows)
    beats={s:n for s,n in counts.items() if s not in {'+','~','[',']','"','|','(',')','!','p','t','u','T','P','s','B','^'}}
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    s=_styles();story=[]
    _header(story,'Published reference material / review record',f'{source_label} - annotation inventory',
            'A review of imported expert annotations. No automated AI detections or clinical performance results are contained here.',s)
    _section(story,'Data summary',s)
    story.append(_table([['Measure','Observed'],
                         ['Annotations (all symbols)',_num(len(rows))],
                         ['Beat-labelled annotations',_num(sum(beats.values()))],
                         ['Non-beat annotations',_num(len(rows)-sum(beats.values()))],
                         ['Last annotation time',f"{max(r['time_s'] for r in rows):,.3f} s"],
                         ['Nominal source sampling rate',f'{sample_rate} Hz'],
                         ['AI detector results','Not evaluated']], [90*mm,CONTENT_W-90*mm],s=s))
    _section(story,'Annotation code breakdown',s)
    symbols=[['Official annotation symbol','Count','Meaning / study handling']]
    meanings={'N':'Normal beat annotation','A':'Atrial premature beat annotation',
              'V':'Premature ventricular beat annotation','+':'Rhythm information; not a heartbeat'}
    for sym,count in sorted(counts.items(),key=lambda x:(-x[1],x[0])):
        symbols.append([sym,count,meanings.get(sym,'Refer to WFDB annotation definitions')])
    story.append(_table(symbols,[39*mm,26*mm,CONTENT_W-65*mm],s=s))
    _section(story,'Provenance and reproducibility',s)
    _keyvalues(story,[('Original reference file',source.name),
                      ('File SHA-256',digest),
                      ('Source basis','User-provided export from published MIT-BIH .atr reference annotations'),
                      ('Report generation time (UTC)',datetime.now(timezone.utc).isoformat())],s)
    _section(story,'Scientific interpretation',s)
    _paragraph(story,'These reference labels are useful for testing a separate QRS detection or beat classification algorithm. A reference label alone is not a prediction, and a high proportion of normal reference beats does not measure algorithm performance.',s)
    _paragraph(story,'The extracted .atr annotations were not independently adjudicated by this application. For a proper detector validation study, retain the original .hea/.dat/.atr files, use a locked detection protocol, compare one-to-one event locations, and report false positives, false negatives, sensitivity, positive predictive value, and confidence intervals.',s)
    _section(story,'Release conclusion',s)
    _paragraph(story,'Reference-data extraction: demonstrated by the supplied annotation CSV. Automated QRS performance: NOT EVALUATED IN THIS REPORT. Clinical validity and deployment authorization: NOT ESTABLISHED.',s)
    _make_doc(path,'VIGIL Studio - MIT-BIH Reference Annotation Review').build(story)
    return Path(path)
