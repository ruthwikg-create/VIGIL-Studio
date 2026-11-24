# VIGIL Studio preliminary threat model — research only

## Assets
Raw waveform samples, annotations, research labels, source metadata, model weights, experiment manifests and local audit logs. For *future* clinical use, PHI and patient identity become especially sensitive.

## Trust boundaries
1. Removable/local research recordings → parsing modules (CSV, NPZ, WFDB, EDF/BDF).
2. User UI actions → SQLite and compressed raw sample archive.
3. Workstation → exported PDFs/CSVs/JSON/ZIPs.
4. Optional downloader / package manager → downloaded models, training data and Python dependencies.
5. Future HIS/EHR/monitor interfaces **not implemented or permitted**.

## Threats and residual gaps
| Threat | Current control | Remaining risk / action |
|---|---|---|
| Tampered waveform archive | New stored SHA-256 + check on load | Local DB and artifact can both be edited by a privileged attacker; off-host signed ledger required |
| Corrupt / compressed archive | ZIP metadata, count and size preflight; NumPy pickle loading disabled | Further fuzzing, process isolation, parsing library CVEs |
| Data loss or silent channel collision | Normalized duplicate CSV header rejection | Need EDF/WFDB mapping and device-level unit validation |
| CSV formula injection | Prefix spreadsheet-dangerous text in exports | Further tests of all exports and downstream consumers |
| Unauthorized access | None: single user local workstation | **BLOCKER:** hospital SSO/MFA/RBAC, security policies, disk encryption, session timeouts |
| Sensitive-data leakage | Heuristic PII-column checks and warnings | **BLOCKER:** not a general de-identification tool; enforce clinical data governance before using PHI |
| Lost or altered audit | Local hash chain and checker | **BLOCKER:** independent log server, signing, retention, clock integrity |
| Model/data poisoning | Model hash verification in optional engine; human labels | Independent dataset provenance, site review, ML supply-chain threat evaluation |
| Unapproved clinical use | Research-only UI and explicit blocked clinical gate | Workflow misuse can still occur; training and independent deployment restrictions |
| Faulty hospital interface | No live hospital interface provided | Must design and validate from hospital specifications before integration |

**Risk acceptance is not established.** This model is preliminary and requires specialist review and traceability to controlled engineering requirements.
