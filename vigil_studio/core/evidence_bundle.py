"""Controlled research evidence bundle: styled PDF + raw machine-readable outputs.

No waveform arrays, authentication credentials, medical clearance assertions, or
unverified clinical labels are bundled. Case JSON can contain reviewer notes;
callers must check de-identification and recipient authorization.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import html
import json
import tempfile
import zipfile

from .reporting import pdf_report, export_window_csv


DICTIONARY = [
    ('quality_score','Unitless, 0-1','Exploratory uncalibrated heuristic; not accuracy or diagnosis'),
    ('availability','Proportion, 0-1','Share of finite sample observations'),
    ('start_s','Seconds','Window start time relative to recording'),
    ('end_s','Seconds','Window end time relative to recording'),
    ('flatline_fraction','Proportion, 0-1','Software-estimated low-variation fraction'),
    ('high_frequency_fraction','Proportion','Exploratory high-frequency content descriptor'),
    ('dynamic_range','Signal-native units','Raw dynamic range descriptor, depends on input calibration'),
    ('std','Signal-native units','Window standard deviation'),
    ('mad','Signal-native units','Median absolute deviation'),
    ('derivative_rms','Signal-native units/sample','RMS of adjacent differences'),
    ('range_99_1','Signal-native units','99th percentile minus 1st percentile'),
    ('nonfinite_fraction','Proportion, 0-1','Missing or nonfinite samples'),
    ('flags','Text','Unvalidated software heuristic flags'),
    ('label','Text','Software window label, not expert reference ground truth'),
]


def _index_html(rec, analysis, assets):
    x=lambda a:html.escape(str(a),quote=True)
    rows=''.join('<tr><td>'+x(name)+'</td><td>'+x(d.get('kind','OTHER'))+'</td><td>'+
                 (f"{d.get('quality',{}).get('quality_score',0):.3f}" if d.get('quality',{}).get('quality_score') is not None else 'Not measured')+
                 '</td><td>'+x(', '.join(d.get('quality',{}).get('flags',[])) or 'None')+'</td></tr>'
                 for name,d in analysis.get('channels',{}).items())
    files=''.join('<li><strong>'+x(n)+'</strong> <span>'+x(desc)+'</span></li>' for n,desc in assets)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>VIGIL Studio | Research evidence index</title>
<style>
:root{{--ink:#213133;--copper:#ce6746;--teal:#147d80;--sand:#f3f5f1;--line:#d8e1dc;--muted:#5c716f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--sand);color:var(--ink);font:15px/1.6 system-ui,'Segoe UI',sans-serif}}
header{{background:var(--ink);color:white;padding:26px max(25px,calc((100% - 980px)/2));font-weight:700;letter-spacing:.09em}}
header em{{color:var(--copper);font-style:normal}}main{{max-width:980px;margin:auto;padding:44px 24px 80px}}
.kicker{{color:var(--copper);letter-spacing:.13em;font-weight:800;font-size:12px;text-transform:uppercase}}
h1{{font-size:35px;line-height:1.2;margin:10px 0}}.sub{{color:var(--muted);max-width:760px}}
.alert{{border-left:4px solid var(--copper);background:white;padding:16px 20px;margin:24px 0}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin:25px 0}}
.stat{{padding:18px;background:white;border:1px solid var(--line)}}.stat small{{display:block;font-size:12px;color:var(--muted);text-transform:uppercase}}
.stat strong{{font-size:22px}}section{{background:white;border:1px solid var(--line);padding:26px;margin:20px 0}}
h2{{font-size:20px;margin:0 0 15px}}table{{width:100%;border-collapse:collapse}}th{{background:var(--ink);color:white;text-align:left}}
th,td{{padding:10px;border-bottom:1px solid var(--line)}}tr:nth-child(even) td{{background:var(--sand)}}
li{{padding:8px 0}}li span{{display:block;color:var(--muted);font-size:13px}}
footer{{margin-top:40px;color:var(--muted);font-size:12px}}code{{word-break:break-all}}
</style></head><body>
<header><em>▰</em> VIGIL STUDIO &nbsp; / &nbsp; INSTRUMENT WORKBENCH</header>
<main><div class="kicker">Research data package / Controlled export</div>
<h1>{x(rec.name)}</h1><p class="sub">Exported observations, analysis windows and provenance. The accompanying PDF is the professionally formatted document; CSV and JSON remain unmodified machine-readable scientific data.</p>
<div class="alert"><strong>RESEARCH USE ONLY.</strong> The source data and heuristics have not been clinically validated. This package does not permit diagnosis, treatment, or control of bedside monitoring systems.</div>
<div class="stats"><div class="stat"><small>Channels</small><strong>{len(rec.channels)}</strong></div><div class="stat"><small>Sample rate</small><strong>{rec.fs:g} Hz</strong></div><div class="stat"><small>Duration</small><strong>{rec.duration:.1f} s</strong></div><div class="stat"><small>Analysis</small><strong>{x(analysis.get('overall','N/A'))}</strong></div></div>
<section><h2>Channel measurements</h2><table><thead><tr><th>Channel</th><th>Modality</th><th>Index*</th><th>Flags</th></tr></thead><tbody>{rows}</tbody></table>
<p style="color:var(--muted);font-size:12px">*Heuristic index. Not a calibrated probability or clinical accuracy score.</p></section>
<section><h2>Included evidence</h2><ul>{files}</ul></section>
<section><h2>Source provenance</h2><p><strong>Origin:</strong> {x(rec.origin)}</p><p><strong>SHA-256:</strong> <code>{x(rec.sha256)}</code></p><p><strong>Analysis engine:</strong> {x(analysis.get('engine','Unknown'))}</p></section>
<footer>VIGIL Studio | Developed By Ruthwik Goparaju<br>These data are not a substitute for clinician review or independent device validation.</footer>
</main></body></html>'''


def export_evidence_package(ws,case_id,rec,analysis,output_path):
    """Create a reproducible dossier ZIP without embedding raw waveform samples.

    The caller must confirm that recorded metadata and reviewer notes are
    de-identified and that the recipient is authorized for these research files.
    """
    output=Path(output_path)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vigil_evidence_') as temp:
        root=Path(temp)
        pdf_report(rec,analysis,ws.reviews(case_id),root/'VIGIL_Research_Dossier.pdf')
        export_window_csv(analysis,root/'quality_windows.csv')
        ws.export_case_json(case_id,root/'case_metadata.json')
        with (root/'DATA_DICTIONARY.csv').open('w',encoding='utf-8',newline='') as f:
            wr=csv.writer(f);wr.writerow(['column','units','scientific_description']);wr.writerows(DICTIONARY)
        assets=[('VIGIL_Research_Dossier.pdf','Branded, paginated report with waveform plots and research limitations'),
                ('quality_windows.csv','Complete window-by-window descriptors for external analysis'),
                ('case_metadata.json','Case metadata and saved research reviews; no raw arrays'),
                ('DATA_DICTIONARY.csv','Column definitions and units'),
                ('MANIFEST.json','File hashes for detecting later modification'),
                ('EVIDENCE_INDEX.html','Human-readable offline cover and contents')]
        (root/'EVIDENCE_INDEX.html').write_text(_index_html(rec,analysis,assets),encoding='utf-8')
        (root/'READ_FIRST.txt').write_text(
            'VIGIL Studio - Research evidence package\n'
            'Developed By Ruthwik Goparaju\n\n'
            'RESEARCH ONLY. NOT FOR PATIENT CARE.\n'
            'Source waveforms are NOT packaged. JSON may include researcher notes.\n'
            'Only share de-identified data after confirming permissions and recipients.\n'
            'A completed benchmark does not establish clinical authorization.\n',encoding='utf-8')
        files=sorted(p for p in root.iterdir() if p.is_file())
        manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
                  'record_name':str(rec.name),'source_sha256':str(rec.sha256),
                  'clinical_use_authorized':False,
                  'raw_waveforms_embedded':False,
                  'files':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes':p.stat().st_size} for p in files}}
        (root/'MANIFEST.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
            for p in sorted(root.iterdir()):z.write(p,arcname=p.name)
    return output


# A checksum manifest verifies consistency of the export files; it is NOT an
# independent signature or evidence that the clinical data are truthful.
MAX_PACKAGE_FILE_BYTES = 120 * 1024 * 1024
MAX_PACKAGE_TOTAL_BYTES = 250 * 1024 * 1024
REQUIRED_PACKAGE_ASSETS = frozenset({
    'VIGIL_Research_Dossier.pdf', 'quality_windows.csv', 'case_metadata.json',
    'DATA_DICTIONARY.csv', 'EVIDENCE_INDEX.html', 'READ_FIRST.txt', 'MANIFEST.json',
})


def verify_evidence_package(source):
    """Read-only verification; never extracts or executes untrusted ZIP contents."""
    source = Path(source)
    with zipfile.ZipFile(source, 'r') as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValueError('Evidence package contains duplicate filenames')
        if set(names) != REQUIRED_PACKAGE_ASSETS:
            raise ValueError('Evidence package has missing or unexpected entries')
        if any(info.is_dir() or info.flag_bits & 0x1 for info in infos):
            raise ValueError('Unsupported encrypted entry or directory')
        if any(info.file_size > MAX_PACKAGE_FILE_BYTES for info in infos):
            raise ValueError('Evidence package contains an oversized entry')
        if sum(info.file_size for info in infos) > MAX_PACKAGE_TOTAL_BYTES:
            raise ValueError('Evidence package exceeds safety limit')
        manifest = json.loads(archive.read('MANIFEST.json'))
        if manifest.get('clinical_use_authorized') is not False:
            raise ValueError('Evidence manifest has invalid clinical-use assertion')
        if manifest.get('raw_waveforms_embedded') is not False:
            raise ValueError('Evidence manifest has invalid raw-waveform assertion')
        expected = set(names) - {'MANIFEST.json'}
        entries = manifest.get('files')
        if not isinstance(entries, dict) or set(entries) != expected:
            raise ValueError('Manifest has incomplete or unexpected file records')
        for name in sorted(expected):
            info = archive.getinfo(name)
            data = archive.read(name)
            declared = entries[name]
            if not isinstance(declared, dict) or declared.get('bytes') != len(data):
                raise ValueError(f'Incorrect manifest size for {name}')
            if declared.get('sha256') != hashlib.sha256(data).hexdigest():
                raise ValueError(f'Evidence file hash mismatch: {name}')
        return {'verified': True, 'files_checked': len(expected),
                'record_name': manifest.get('record_name'),
                'source_sha256': manifest.get('source_sha256'),
                'clinical_use_authorized': False,
                'note': 'Content integrity only; no independent digital signature or clinical approval.'}
