"""Independent-readable clinical readiness gate report; authorization is never implied.

Only local source/workspace evidence is collected. No patient or signal values are exported.
Medical claims can never be inferred solely from passed tests or a UI checkbox.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import hashlib, json, sys

GATES = (
    ('G-01', 'Specified clinical intended use and device classification', 'BLOCKED',
     'Clinical sponsor/regulatory lead must approve a narrow intended use and classify each clinical module.'),
    ('G-02', 'QMS, configuration management and lifecycle processes', 'BLOCKED',
     'Establish an operating ISO 13485-compatible QMS and IEC 62304 development evidence.'),
    ('G-03', 'Risk controls and residual-risk approval', 'BLOCKED',
     'Hazard analysis, verification of risk controls, clinical risk acceptability sign-off.'),
    ('G-04', 'Analytical performance on independent clinical data', 'BLOCKED',
     'Locked protocol, independent dataset, predefined acceptance, complete failure analysis.'),
    ('G-05', 'Human clinical validation and usability', 'BLOCKED',
     'Clinical evidence, observed use testing, human factors, hospital sponsor and approvals.'),
    ('G-06', 'Clinical cybersecurity and privacy safeguards', 'BLOCKED',
     'Authenticated role access, encryption/key management, device/network threat model, security testing.'),
    ('G-07', 'Hospital interfaces and safe operations', 'BLOCKED',
     'Approved HIS/EHR interfaces, reconciliation, downtime operations and clinical acceptance testing.'),
    ('G-08', 'Applicable regulatory permissions', 'BLOCKED',
     'Regulatory submissions/authorizations determined by intended use, jurisdiction and product classification.'),
)


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open('rb') as fh:
        for part in iter(lambda:fh.read(1024*1024),b''):
            digest.update(part)
    return digest.hexdigest()


def assess_workspace(workspace) -> dict:
    """Collect local integrity evidence without any raw physiological samples."""
    audit = workspace.verify_audit()
    assets = workspace.verify_record_integrity()
    passed = audit['valid'] and assets['total']>0 and assets['failed']==0 and assets['unverified_legacy']==0
    return {'engineering_integrity': ('NO_RECORDINGS' if assets['total']==0 else ('PASS' if passed else 'REVIEW_REQUIRED')),
            'audit':audit,'case_files':assets,
            'warning':'Passing local integrity checks is not clinical validation, security attestation, or patient-use authorization.'}


def assess_release(workspace=None, benchmark_dir=None, *, audit_anchor_path=None, audit_key_path=None) -> dict:
    """Explicitly fail closed: no automatic gate can authorize patient care."""
    integrity = assess_workspace(workspace) if workspace is not None else {'engineering_integrity':'NOT_CHECKED'}
    benchmark = {'status':'NOT_PROVIDED'}
    if benchmark_dir:
        base=Path(benchmark_dir).expanduser().resolve()
        run=base/'results.json'
        # The benchmark's local output is only engineering evidence, never proof of clinical validity.
        if not run.is_file():
            benchmark={'status':'MISSING', 'note':'Benchmark result file was not found'}
        else:
            try:
                data=json.loads(run.read_text(encoding='utf8'))
                status=data.get('completion_status')
                expect=data.get('preflight',{}).get('expected_records',[])
                records=data.get('records',[])
                protocol=data.get('protocol',{})
                necessary=('locked_protocol.json','per_record_metrics.csv','REPORT.md')
                files_ok=all((base/name).is_file() for name in necessary)
                matched=(status=='COMPLETED' and isinstance(expect,list) and len(expect)>0
                         and isinstance(records,list) and len(records)==len(expect)
                         and not data.get('errors') and data.get('research_only') is True
                         and protocol.get('clinical_grade') is False and files_ok)
                benchmark={'status': 'COMPLETE_RESEARCH_BENCHMARK' if matched else 'INCOMPLETE_OR_UNVERIFIED',
                           'sha256':_sha256(run),'completion_status':status,
                           'record_count':len(records) if isinstance(records,list) else None,
                           'note':'Self-reported local research benchmark; not independently validated or clinical evidence'}
            except (OSError,ValueError,TypeError) as exc:
                benchmark={'status':'UNREADABLE','error_type':type(exc).__name__}
    # These controls are deliberately NOT represented as clinical release passes.
    security_controls = {
        'existing_workspace_encrypted_at_rest': False,
        'hospital_staff_authentication_and_rbac': False,
        'external_identity_provider_integrated': False,
        'encrypted_research_export_available': False,
        'external_audit_anchor': {'status':'NOT_CONFIGURED'},
        'hospital_security_review_complete': False,
    }
    try:
        from .encrypted_export import _aes
        _aes()
        security_controls['encrypted_research_export_available']=True
    except (ImportError, RuntimeError):
        pass
    if audit_anchor_path is not None or audit_key_path is not None:
        if not (audit_anchor_path and audit_key_path and workspace is not None):
            security_controls['external_audit_anchor']={'status':'MISSING_ARGUMENT'}
        else:
            from .audit_anchor import verify_anchor
            check=verify_anchor(workspace,audit_key_path,audit_anchor_path)
            security_controls['external_audit_anchor']={'status':'VERIFIED_LOCAL_ANCHOR' if check['valid'] else 'INVALID_ANCHOR', **check}
    return {'schema':'vigil-hospital-readiness-gate-v2','security_controls':security_controls,
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'product':'VIGIL Studio 4.8 (professional research evidence build)',
            'intended_use':'Offline analysis of consented, properly de-identified research signals only',
            'clinical_operations_authorized':False,
            'clinical_release_decision':'BLOCKED',
            'engineering_checks':integrity,'retrospective_benchmark':benchmark,
            'clinical_gates':[{'id':id,'name':name,'state':status,'required_evidence':evidence}
                              for id,name,status,evidence in GATES],
            'limitation':'This automatically generated checklist cannot grant clinical approval or replace independent signed evidence.'}


def render_markdown(report:dict) -> str:
    rows=['# VIGIL Studio — hospital readiness engineering check','',
          '**CLINICAL RELEASE BLOCKED — NOT FOR PATIENT CARE**','',
          f"Generated: {report['generated_utc']}",
          f"Research-only intended use: {report['intended_use']}",
          f"Local engineering integrity: {report['engineering_checks'].get('engineering_integrity','NOT_CHECKED')}",
          f"MIT-BIH retrospective evidence: {report['retrospective_benchmark']['status']}",
          f"External audit anchor: {report.get('security_controls',{}).get('external_audit_anchor',{}).get('status','NOT_CHECKED')}",
          'Original research workspace is NOT encrypted at rest. Optional AES-GCM encrypted exports do not change that.',
          'Clinical staff authentication and hospital security review are NOT implemented.','', 
          '| Gate | Area | State | Evidence needed |','|---|---|---|---|']
    for item in report['clinical_gates']:
        rows.append(f"| {item['id']} | {item['name']} | {item['state']} | {item['required_evidence']} |")
    rows+=['','Engineering verification is not a license, certification, clinical trial, or proof of medical safety.',
           'No live alarm, diagnosis, triage or patient-management action is implemented or authorized.']
    return '\n'.join(rows)+'\n'


def write_report(report:dict,out:Path):
    """Create a new report directory without overwriting prior evidence."""
    out=Path(out).expanduser().resolve()
    out.mkdir(parents=True,exist_ok=False)
    (out/'READINESS.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    (out/'READINESS.md').write_text(render_markdown(report),encoding='utf8')
    from vigil_studio.core.professional_reports import write_readiness_pdf
    write_readiness_pdf(report,out/'READINESS_ASSESSMENT.pdf')
    return out
