# VIGIL Studio v4.6 — Hospital-readiness engineering audit
**2026-11-24 | Research engineering release | Clinical deployment: BLOCKED**

## Executive decision
VIGIL is a native, single-user, offline **research analysis workstation**. It has not been validated as a clinical device; do not deploy to live patients, use to suppress alarms, diagnose disease, choose treatment, triage patients, or connect to a production hospital information system. A doctor requesting the project does not confer regulatory authorization.

## Proposed, deliberately narrow *candidate* clinical intended use (requires sponsor approval)
An **offline, clinician-reviewed ECG annotation and beat-location inspection aid** for archived, appropriately obtained ECG recordings. The software would display signal morphology, expert annotations, and potentially independently computed peak positions, with explicit uncertainty, source identity and review provenance. It is **not** proposed for autonomous arrhythmia diagnosis, real-time monitoring, alarm management or prescribing.

Do not label this a finalized intended use until the clinical sponsor, manufacturer, regulatory lead and quality manager approve it. Broader EEG, PPG, respiratory, AI foundation and hospital workflows would each need separate justification, hazard review and clinical evidence.

## Findings from actual code review
| ID | Actual source observation | Risk | v4.6 change | What still needs to happen |
|---|---|---|---|---|
| A-01 | `core/store.py` persisted compressed raw samples in NPZ, source SHA-256 only | Undetected changes to saved NPZ | Store saved-archive SHA-256 for new cases; check before loading; preserve prior records as *unverified legacy* | Off-host immutable log, encryption, backups and independent audit |
| A-02 | `core/records.py` loaded untrusted NPZ via `np.load(allow_pickle=False)` | Resource exhaustion from malicious ZIP content | Precheck ZIP names, counts, metadata and decompressed size | Sandboxing and fuzzing against malformed files |
| A-03 | `core/importers.py` did not block `patient id` normalization and normalized header collisions | Accidental identity fields, silent channel loss | Expanded identifier-header denylist, normalized duplicate detection | Full DICOM/FHIR/EDF/WFDB PHI threat analysis; clinical import governance |
| A-04 | CSV exports included untrusted channel/group text | Formula injection in spreadsheet tools | Prefix formula-like text to prevent execution when opened as CSV in spreadsheet applications | Cross-format export test suite, privacy approval and DLP controls |
| A-05 | `core/ecg_validation.py` uses a simple research beat detector | Misses and false events may be clinically consequential | No algorithm claim changed; fixed-protocol MIT-BIH research benchmark retained | Predefined acceptance, locked algorithm, independent multicentre evaluation, clinical harm analysis |
| A-06 | `core/store.py` uses single-user local SQLite with hash-chain audit | No roles/identity, audit can be rewritten by host administrator | Read-only engineering integrity inventory and readiness report | Clinical identity, least privilege, cryptographic signing, centralized SIEM, immutable retention |
| A-07 | `ui/app.py` and export routines expose research analysis | Clinical overreliance, workflow misuse | Visible BLOCKED status in Guide & Safety, explicit offline command report | Human-factors studies, IFU, clinician workflow requirements and supervised pilots |
| A-08 | `requirements.txt` specifies version ranges | Reproducibility / vulnerability control gaps | Environment snapshot tool | Approved Windows binary, complete pinned/hashed dependency lock, SBOM, SCA/CVE review, release signoff |
| A-09 | `scripts/clinical_readiness_benchmark.py` tests MIT-BIH beat locations, not diagnosis | Misreading F1 as regulatory readiness | Separate formal gate output; missing evidence never auto-passes | External site data and clinical validation under approved protocol |

The wording “research-only” is a **safety restriction**, not proof that de-identification, storage security or experimental controls are sufficient.

## Release gates (none are automatically approvable)
| Gate | Owner | Evidence required | v4.6 result |
|---|---|---|---|
| G-01 Approved intended use and risk classification | Clinical sponsor / regulatory lead | Signed statement, patient population, environment, role, outputs, harms, applicable CDSCO category | BLOCKED |
| G-02 Controlled QMS | Manufacturer / quality manager | ISO 13485-aligned documents and records, IEC 62304 lifecycle plan, controlled design reviews | BLOCKED |
| G-03 Risk acceptability | Clinical risk owner | ISO 14971 hazard analysis, mitigations, verification, residual risk decision | BLOCKED |
| G-04 Analytical validation | Independent verification lead | Real ECG full dataset and external sites, preregistered acceptance, missingness/shift/stress tests | BLOCKED |
| G-05 Clinical & human factors | Qualified investigators | Independent clinical validity and IEC 62366-1 usability evidence | BLOCKED |
| G-06 Security & privacy | Hospital IT/security/DPO | Network/host control, encryption, RBAC/SSO, access log, penetration test, data governance | BLOCKED |
| G-07 Hospital integration / continuity | Hospital IT/biomedical staff | Interface test environment, HL7/FHIR mapping if applicable, downtime/recovery, alarm separation | BLOCKED |
| G-08 Regulatory permissions | Regulatory affairs / legal | Applicable test/clinical/market permissions, registration/licence, postmarket plan | BLOCKED |

The in-app and CLI gate checker only reports **local engineering evidence**. It never changes a clinical release decision to PASS. Its audit chain is not independently anchored; anyone with enough access to the filesystem can change the database and its local checksums.

## Verification programme
1. **Functional and negative controls:** Run tests on Windows 11 with Python 3.12; use corrupted files, missing columns/labels, duplicate channels, time glitches, NaN/Inf and compressed-archive attacks. Retain screenshots and signed test logs.
2. **Data and provenance:** Assess all original MIT-BIH records using untouched `.hea`, `.dat`, `.atr`. Verify file identities and label handling. Never report the experiment's scores as clinical sensitivity for diagnosis.
3. **External generalization:** Register external datasets and separate development/site/subject groups before looking at performance. Include devices, populations, signal quality, low amplitude, pacing, arrhythmias, ectopy and noise; disclose site differences.
4. **Risk-driven testing:** Each hazard must have a requirement, test, result, severity, residual risk, owner and approval. **Do not** resolve hazards using invented probabilities.
5. **Security:** Static/dynamic analysis, SCA/SBOM, authz, encryption/storage policy, backup/restore, logging, vulnerability response, patch/rollback and independent penetration testing.
6. **Clinical workflow:** Observe actual clinician tasks with realistic simulated cases and documented errors; test readability, mistaken units, unavailable data and ambiguous ECG morphology.
7. **Silent clinical pilot:** Only after hospital governance, permitted data protection controls, independent ethics determination/approval and applicable regulatory route. No AI output can alter patient management at this stage.
8. **Clinical/market deployment:** Only once the manufacturer/hospital and appropriate authority have accepted the complete device dossier and site controls.

## Source framework (official)
- India CDSCO, **Medical Device Software under MDR-2017, July 21 2026**, official PDF: https://www.cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/Guidance-document-on-Medical-Device-Software-under-MDR-2017.pdf
- IEC 62304 software lifecycle: https://www.iso.org/standard/38421.html
- IEC 82304-1 general health software product safety: https://www.iso.org/standard/59543.html
- IMDRF/SaMD clinical evaluation (valid clinical association, analytical validation, clinical validation): https://www.imdrf.org/documents/software-medical-device-samd-clinical-evaluation
- ISO 14971 risk management standard listing: https://www.iso.org/standard/72704.html
- TGA’s publicly accessible standards overview: https://www.tga.gov.au/products/medical-devices/software-and-artificial-intelligence-ai/overview/standards-software-based-medical-devices
- US FDA QMSR as of Feb 2 2026 (relevant *only* if targeting the US): https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/quality-and-compliance-medical-devices
- India DPDP Act/Rules privacy framework, phased implementation must be confirmed with hospital counsel: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025
- FHIR R4 security context (not a secure hospital integration by itself): https://hl7.org/fhir/R4/security.html

**Regulatory reference ≠ proof of compliance.** Applicability, risk class and legal obligations must be decided by qualified representatives and the relevant regulator under the actual intended use.
