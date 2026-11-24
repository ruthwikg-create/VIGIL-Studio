"""Real report output tests: synthetic signal fixtures, no patient data."""
import io
import json
import zipfile
from pathlib import Path

import pytest

from vigil_studio import __version__
from vigil_studio.core.demo import make_demo
from vigil_studio.core.processing import analyze_record
from vigil_studio.core.store import Workspace
from vigil_studio.core.reporting import pdf_report
from vigil_studio.core.evidence_bundle import export_evidence_package, verify_evidence_package
from vigil_studio.core.professional_reports import (write_readiness_pdf,write_benchmark_pdf,
    write_reference_summary_pdf)
from vigil_studio.safety.gates import assess_release,write_report


def _fixture(tmp_path):
    rec = make_demo(seconds=20,seed=9)
    analysis = analyze_record(rec)
    ws = Workspace(tmp_path/'workspace')
    cid = ws.add_case(rec,analysis)
    ws.add_review(cid,'needs_review','Synthetic verification only')
    return ws,cid,rec,analysis


def _pdf_text(path):
    fitz=pytest.importorskip('fitz',reason='Optional PDF text inspection library not installed')
    with fitz.open(path) as doc:
        return len(doc), '\n'.join(page.get_text() for page in doc)


def test_scientific_dossier_has_factual_sections(tmp_path):
    ws,cid,rec,analysis = _fixture(tmp_path)
    output=pdf_report(rec,analysis,ws.reviews(cid),tmp_path/'sample.pdf')
    pages,txt=_pdf_text(output)
    assert pages>=4
    for word in ('Physiological signal analysis','Recording provenance',
                 'SYNTHETIC_BASELINE','Window-by-window quality review',
                 'Review, limitations', 'NOT ESTABLISHED','NOT FOR CLINICAL DECISIONS'):
        assert word in txt
    assert 'Developed By Ruthwik Goparaju' in txt
    assert 'Synthetic verification only' in txt
    assert 'Not for diagnosis' not in txt or 'NOT FOR CLINICAL DECISIONS' in txt


def test_evidence_bundle_verifies_and_detects_tamper(tmp_path):
    ws,cid,rec,analysis = _fixture(tmp_path)
    dest=export_evidence_package(ws,cid,rec,analysis,tmp_path/'evidence.zip')
    state=verify_evidence_package(dest)
    assert state['verified'] and state['files_checked']==6
    with zipfile.ZipFile(dest) as zi:
        names=set(zi.namelist())
        assert 'recording.npz' not in names
        assert 'VIGIL_Research_Dossier.pdf' in names
        assert b'<html' in zi.read('EVIDENCE_INDEX.html')
        doc=json.loads(zi.read('case_metadata.json'))
        assert doc['research_only'] is True
        assert doc['raw_waveforms_not_embedded'] is True
        assert doc['reviews'][0]['note']=='Synthetic verification only'
        content={i.filename:zi.read(i) for i in zi.infolist()}
    content['DATA_DICTIONARY.csv']+=b'\nmalicious change'
    bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(bad,'w') as zo:
        for k,v in content.items():zo.writestr(k,v)
    with pytest.raises(ValueError,match='hash mismatch|manifest size'):
        verify_evidence_package(bad)


def test_evidence_bundle_rejects_missing_duplicates_and_extra(tmp_path):
    ws,cid,rec,analysis = _fixture(tmp_path)
    dest=export_evidence_package(ws,cid,rec,analysis,tmp_path/'evidence.zip')
    with zipfile.ZipFile(dest) as zi:
        content={i.filename:zi.read(i) for i in zi.infolist()}
    for target,exclude,extra in [('missing','READ_FIRST.txt',None),('extra',None,('other.txt',b'extra'))]:
        bad=tmp_path/(target+'.zip')
        with zipfile.ZipFile(bad,'w') as zo:
            for k,v in content.items():
                if k!=exclude:zo.writestr(k,v)
            if extra:zo.writestr(*extra)
        with pytest.raises(ValueError,match='missing or unexpected'):
            verify_evidence_package(bad)


def test_readiness_generates_polished_pdf_without_clinical_approval(tmp_path):
    ws, *_ = _fixture(tmp_path)
    report=assess_release(ws)
    dest=write_report(report,tmp_path/'assessment')
    assert report['engineering_checks']['engineering_integrity']=='PASS'
    assert (dest/'READINESS.json').is_file()
    assert (dest/'READINESS.md').is_file()
    pages,txt=_pdf_text(dest/'READINESS_ASSESSMENT.pdf')
    assert pages>=1
    assert 'Hospital readiness assessment' in txt
    assert 'NOT AUTHORIZED' in txt
    assert 'Local engineering integrity' in txt
    assert 'Clinical release evidence register' in txt
    assert report['clinical_operations_authorized'] is False


def test_partial_benchmark_pdf_reports_missing_coverage(tmp_path):
    run={'completion_status':'INCOMPLETE','created_utc':'2026-11-24T02:30:00+00:00',
         'records':[{'record_id':'100','lead':'MLII','n_reference_beats':20,'tp':18,'fp':1,'fn':2,
                     'sensitivity':0.9,'positive_predictive_value':18/19}],
         'preflight':{'expected_records':['100','101'],'missing':[{'record':'101','missing_files':['101.dat']}], 'empty':[]},
         'errors':[], 'summary':{'pooled':{'tp':18,'fp':1,'fn':2,'sensitivity':.9,
                  'positive_predictive_value':18/19,'f1':36/39}},
         'protocol':{'protocol_id':'FIXED','detector':'EXPLORATORY','scoring':'150 ms'}}
    dest=write_benchmark_pdf(run,tmp_path/'bench.pdf')
    _,txt=_pdf_text(dest)
    assert 'Incomplete / partial' in txt
    assert 'NOT AUTHORIZED' in txt
    assert 'Record-level distribution' in txt
    assert 'Missing: 101' in txt
    assert 'Research outcome' in txt


def test_reference_report_is_reference_not_ai(tmp_path):
    f=tmp_path/'annotations.csv'
    f.write_text('sample,time_s,symbol\n100,0.277778,N\n360,1.0,A\n')
    dest=write_reference_summary_pdf(f,tmp_path/'ref.pdf')
    _,txt=_pdf_text(dest)
    assert 'No automated AI detections' in txt
    assert 'Normal beat annotation' in txt
    assert 'Atrial premature beat annotation' in txt
    assert 'NOT EVALUATED' in txt


def test_duplicate_evidence_archive_entry_rejected(tmp_path):
    ws,cid,rec,analysis=_fixture(tmp_path)
    dest=export_evidence_package(ws,cid,rec,analysis,tmp_path/'out.zip')
    with zipfile.ZipFile(dest) as z:
        body={i.filename:z.read(i) for i in z.infolist()}
    bad=tmp_path/'dup.zip'
    with zipfile.ZipFile(bad,'w') as z:
        for k,v in body.items():z.writestr(k,v)
        with pytest.warns(UserWarning, match='Duplicate name'):
            z.writestr('READ_FIRST.txt',body['READ_FIRST.txt'])
    with pytest.raises(ValueError,match='duplicate'):
        verify_evidence_package(bad)


def test_reference_report_cli_refuses_overwrite(tmp_path):
    from scripts.reference_annotation_report import main
    source=tmp_path/'100_reference_annotations.csv'
    source.write_text('sample,time_s,symbol\n100,0.277778,N\n360,1.0,A\n',encoding='utf-8')
    output=tmp_path/'reference.pdf'
    assert main([str(source),'--out',str(output)])==0
    original=output.read_bytes()
    assert original.startswith(b'%PDF')
    assert main([str(source),'--out',str(output)])==2
    assert output.read_bytes()==original
