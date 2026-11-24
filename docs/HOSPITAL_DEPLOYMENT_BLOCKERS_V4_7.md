# VIGIL Studio v4.7 — clinical release blockers and hospital handoff

**Status: CLINICAL RELEASE BLOCKED.** This is a research software engineering build, not an authorized medical device, patient monitor, alarm system, or diagnostic product.

## Scope locked for this release

- **Actual intended use:** offline educational and de-identified research waveform review, human annotations, experimental QRS-location analysis, and retrospective benchmark creation.
- **Excluded:** diagnosing arrhythmia, clinical alerts, deciding treatment, monitoring current patients, clinical triage, automated alarm suppression, driving actuators, import/export of identifiable hospital records.
- **No clinical-facing 'unlock' exists**. A hospital software verification checklist cannot grant regulatory permission.

## Software audit, risk, evidence

| ID | Deficiency / hazard | Implemented in v4.7 | Remaining for clinical release |
|---|---|---|---|
| G01 | No clinically approved intended use / classification | Scope and sponsor worksheet documented | Hospital sponsor defines target population, users, claims; regulatory specialist assesses Indian MDR-2017 class, if applicable |
| G02 | No operational medical QMS | Requirements/risk/test traceability, tests, evidence snapshots | Controlled ISO 13485 procedures, configuration records, lifecycle sign-offs, design reviews and CAPA processes |
| G03 | Unclosed hazards, patient harm risks | Risk register and fail-closed benchmark status; secure import/export checks | ISO 14971 risk acceptability review, FMEA, verification of all risk controls, independent human factors assessment |
| G04 | Insufficient model performance evidence | Fixed MIT-BIH 48-record runner; no accuracy fabrication | Completed original-data evaluation, predefined clinical acceptance criteria, independent external data, subgroups, difficult cases and reproducibility |
| G05 | No prospective clinical use evaluation | No patient-care actions implemented | Ethical review and prospective silent-mode/clinical studies as appropriate, clinical study protocol and qualified investigator oversight |
| G06 | Unprotected local workspace and absent user identity | Optional **encrypted case export**, **separate-key HMAC audit anchor**, safer CSV imports; export warnings | Actual workspace database encryption, clinical user SSO/MFA/RBAC, sessions, revocation, secure backup/retention, pen testing, key management, ransomware recovery, privacy assessment |
| G07 | No validated hospital interfaces and workflows | Research-only offline mode; no live device interface | Hospital IT EHR interface specifications, interoperability, fail-safe offline mode, downtime and reconciliation tests, monitored deployment and change control |
| G08 | No authorization | Explicit hard-block in all reports and UI | Applicable CDSCO permissions and other local approvals confirmed and obtained by authorized parties |

## Additional v4.7 engineering controls

1. `safety/encrypted_export.py`: optional authenticated AES-256-GCM export, fresh per-file nonce/salt, scrypt KDF, strong passphrase, create-only files, 96 MiB input limit, verified source digest requirement. **Existing unencrypted records are NOT encrypted by this feature.**
2. `safety/audit_anchor.py`: optional SHA-256/HMAC external seal of local audit-event chain; detects changes or truncation relative to an operator-held off-workspace key and snapshot. Does **not** substitute for off-host immutable centralized logs.
3. `core/importers.py`: bounded CSV cell-count to reduce out-of-memory imports.
4. `scripts/collect_engineering_evidence.py`: self-run pytest evidence, dependency inventory and SHA-256 code manifest, with test outcome explicitly recorded.
5. GUI requires confirmation before exporting unencrypted raw waveform CSV or case ZIP; Guide & Safety exposes research security guidance.
6. The readiness report includes whether the optional audit anchor was verified and states that original workspaces remain unencrypted.

## Evidence status (not claims of conformity)

| Evidence | Status |
|---|---|
| Existing software regression + new negative security tests | Executed, see `TEST_RESULTS.md` and `verification_evidence/` |
| Native desktop startup and 14 sections | Tested in virtual Linux display; Windows validation outstanding |
| 48-record MIT-BIH full benchmark | NOT EXECUTED in this build environment; requires original dataset on researcher's Windows laptop |
| Hospital penetration test / key-management integration | NOT PERFORMED |
| Clinical acceptance thresholds / external hospital data | NOT ESTABLISHED |
| Human factors, usability and IEC 62304/ISO 14971 controlled-process signoff | NOT PERFORMED |
| Appropriate regulatory permission | NOT ESTABLISHED |

## Doctor/clinical engineering owner must supply

- Product manufacturer/organization and accountable clinical sponsor.
- Intended medical purpose; target workflow and users; patient populations and environments; explicit patient-impacting outputs.
- Monitor/manufacturer, hardware/signal acquisition, sample rates, datasets and calibration requirements.
- Clinical false-negative/false-positive tolerances, study endpoints, statistical analysis plan and independent evaluation datasets.
- Hospital IT security architecture, DPO/security officer, EHR or DICOM/FHIR requirements, protected health information policies, incident-response and backup procedures.
- Qualified quality/regulatory personnel; ethics and study permissions; incident response and deployment authorization workflow.

## Official resources to interpret with the actual standards and legal advisors

- [CDSCO: Guidance on Medical Device Software under MDR-2017 (21 Jul 2026)](https://www.cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/Guidance-document-on-Medical-Device-Software-under-MDR-2017.pdf)
- [IEC 62304 lifecycle standard](https://webstore.iec.ch/en/publication/22794)
- [US FDA QMSR (effective 2 Feb 2026)](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/quality-and-compliance-medical-devices) — US reference; does not replace applicable Indian law
- [US FDA 2026 medical device cybersecurity guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cybersecurity-medical-devices-quality-management-system-considerations-and-content-premarket) — relevant engineering reference
- [OWASP ASVS 5.0](https://github.com/OWASP/ASVS) — general application security reference, not medical-device certification
