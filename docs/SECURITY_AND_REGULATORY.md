# Security, patient privacy and regulatory status

**Clinical status: not authorized, not certified and not evaluated for patient care.** This is research-only software.

- Development decisions explicitly prohibit clinical data streams, interventional alarms and automatic treatment recommendations.
- No software can claim compliance with IEC 62304, ISO 14971, ISO 13485, IEC 62366-1, IEC 81001-5-1 or applicable Indian CDSCO rules simply because those standards are mentioned. A real quality system, independent reviews, controlled artifacts and verified evidence are needed.
- An authorized software-as-a-medical-device intended use may trigger CDSCO regulatory oversight in India and additional approval/clinical investigation requirements. Qualified regulatory advisers and the sponsoring hospital must establish the correct classification and submission.
- The research workstation is **not** hardened for identifiable health records. It stores local raw waveform samples and SQLite metadata in plaintext. Even filenames could contain identifiers, so case importers intentionally do not promise complete de-identification.
- Use only properly licensed, permitted, already de-identified waveform recordings. Encrypt the computer drive, limit accounts, enforce backups, secure exports and obtain hospital permissions if applicable.
- Model JSON is a numeric schema to reduce untrusted pickle-code execution risk; numeric validation does not constitute a full secure codebase audit.
- The audit is a convenience hash chain. Privileged deletion of the entire file or falsifying earlier copies cannot be detected without externally anchored hashes. It is not 21 CFR Part 11 compliance or a clinical record.
- No cloud, telemetry, login, device discovery, or bedside network connection is used. The explicit PhysioNet downloader is a separate user-run helper script and must be reviewed under local policy.
- No clinical sensitivity, specificity, equivalence, medical-grade measurement accuracy or clinical trial success are claimed.
