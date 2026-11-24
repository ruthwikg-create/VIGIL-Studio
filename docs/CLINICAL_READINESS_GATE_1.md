# VIGIL Studio — Medical-device readiness programme, Gate 1

**Status as of 24 November 2026: RESEARCH ONLY; NOT A MEDICAL DEVICE THAT IS AUTHORIZED FOR PATIENT CARE.**

This is a **planning and engineering evidence** package, not an ISO certificate, independent clinical validation, registered clinical trial, CDSCO approval, or advice to use VIGIL on patients.

## 1. Intended use — separate the two products

### Current validated-in-software scope (research tool)

> Offline review of properly permitted, already de-identified physiological recordings; visualization, quality-indicator exploration and reference-annotation comparisons for research. Users can manually annotate experimental records and export research reports. The results are not intended to guide clinical diagnosis, treatment, alarm handling or patient triage.

### Potential future clinical intended use — **not yet agreed/authorized**

A qualified clinical investigator, manufacturer representative and regulatory lead must define the **specific** patient population, intended user, environment, specific measurement/decision, output, acceptable performance, limitations and foreseeable harms. Do NOT use the vague umbrella term 'medical-grade biomedical research environment' as an intended use for a regulatory submission. Different modules may require separate classifications and evidence.

**Recommended first candidate for investigation:** clinician-reviewed, offline ECG beat-location inspection, with no independent clinical diagnosis or alarm suppression. This is a *research candidate*, not an authorized claim.

## 2. Evidence gates and current status

| Gate | Requirement | State on 2026-11-24 | Evidence needed next |
|---|---|---|---|
| V0 | Existing source tests and synthetic functional checks | Software regression checks passed | Repeat in pinned Windows environment |
| V1 | Original MIT-BIH files, 48/48 record coverage, locked benchmark | **NOT RUN on full real dataset in this build environment** | `RUN_MITBIH_VERIFICATION_WINDOWS.bat`, output bundle, independent review |
| V2 | Independent dataset not used to tune algorithms | NOT STARTED | Select and register protocol and licensing before results |
| V3 | Negative controls, synthetic corruption, missingness and timing-shift tests | Partial exploratory fixtures only | Formal test matrix by hazard and required outcome |
| V4 | Source-to-requirement-to-test traceability | DRAFT | Independent requirements review and test signoff |
| V5 | Cybersecurity/privacy risk assessment and penetration testing | NOT COMPLETED | Threat model, encryption/authentication, data handling, testing |
| V6 | Software life-cycle and risk management process | NOT ESTABLISHED | Appropriate QMS, configuration management, hazard control verification |
| V7 | Clinician usability and human factors validation | NOT STARTED | Clinician tasks, use-error analysis, observed usability study |
| V8 | Prospective silent-mode study | NOT AUTHORIZED / NOT STARTED | Hospital sponsor, approvals, ethics review, protocol |
| V9 | Any patient-affecting clinical investigation and applicable authorization | NOT AUTHORIZED / NOT STARTED | Jurisdiction-specific regulatory process and clinical evidence |

**Stop/go rule:** Completing V1 cannot advance the product directly to clinical use. Each gate has distinct evidence requirements. Do not market or use the current software for patient care.

## 3. Fixed MIT-BIH retrospective evaluation plan

- **Dataset:** Official MIT-BIH Arrhythmia Database 1.0.0, all 48 recordings and original `.atr` annotations, without changes to waveform or labels.
- **Task:** Beat **location** agreement only. No beat-type classification or arrhythmia diagnosis.
- **Algorithm:** Unmodified exploratory `vigil_heuristic_peak_finder`, as found in v4.4 source; pre-run source SHA-256 included in locked protocol.
- **Input lead:** MLII when present, otherwise first normalized ECG lead, chosen without reference labels.
- **Scoring:** Independent one-to-one reference-vs-detection position match with a pre-fixed 150 ms tolerance (research test setting, not a clinical acceptance threshold).
- **Outcomes:** TP, FP, FN; sensitivity; positive predictive value; F1; median and p95 absolute timing error; per-record and by-reference-symbol *location detection* breakdown; subject-cluster resampling intervals (records 201 and 202 grouped).
- **Integrity:** `.hea/.dat` identity hash and separate `.atr` hash; result files, protocol and software platform included.
- **Fail/unknown:** Missing/corrupt/truncated or errored files count as an incomplete run, not as successes. Report the reason and retain failed records.
- **Data handling:** Official original files remain read-only; do not upload any identifiable or unapproved clinical data.
- **Performance acceptance:** **NOT YET SET.** A clinician/regulatory/quality team must establish acceptance thresholds based on intended use, clinical harms, reference standard and independent evidence *before* an independent dataset evaluation.

## 4. High-priority hazards to address

See `RISK_REGISTER_DRAFT.csv`. The following are unresolved:

- False negative beat due to signal corruption, narrow QRS or detector failure.
- False positive beat due to motion, pacing artifacts or T-waves.
- ECG lead reversal, unexpected sampling frequency and timestamp alignment.
- Confusing heuristic quality scores with calibrated probabilities.
- Label leakage, dataset duplicates, population and site shift.
- Tampered/corrupted export, accidental relabeling and audit-chain limitations.
- Sensitive health data stored in plaintext, exported without access controls.
- Human overreliance on research-only outputs or suppression of an alarm.

## 5. Regulatory and engineering standards (not compliance claims)

For a product intended for India, see the **CDSCO 2026 medical-device software guidance** under Medical Devices Rules 2017. Scope, risk classification and the correct authorization route must be decided from an actual intended use with qualified regulatory specialists, not guessed from a software name. Relevant software-development reference frameworks may include **IEC 62304:2006+A1:2015** (software lifecycle), **ISO 14971:2019** (risk management), **IEC 62366-1** (usability engineering), **ISO 13485** (quality management) and **IEC 81001-5-1** (health-software cybersecurity), as applicable. These require documented controlled implementation and external evidence; including a checklist does not demonstrate compliance.

Official source starting points:
- https://www.cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/Guidance-document-on-Medical-Device-Software-under-MDR-2017.pdf
- https://webstore.iec.ch/en/publication/22794
- https://www.iso.org/standard/72704.html
- https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/good-machine-learning-practice-medical-device-development-guiding-principles
- https://physionet.org/content/mitdb/1.0.0/

## 6. Data you should return for review

After running `RUN_MITBIH_VERIFICATION_WINDOWS.bat` and choosing **1** for Record 100, send `REPORT.md` and `per_record_metrics.csv` from the generated folder. We can review errors and QRS-location agreement, then move to all 48 records. Do not disclose personal medical records. If all 48 are available, select **2** and preserve that result folder unchanged.
