# Optional research security controls — v4.7

**Never use these instructions with identifiable patient data or as a hospital security substitute.** The old `VIGILStudio_Workspace/research.sqlite3` and `records/*.npz` remain unencrypted.

## 1. Prepare the development environment on Windows

Run `START_WINDOWS.bat` as usual, then `RUN_SECURITY_TESTS_WINDOWS.bat` to install the optional `cryptography` package and run the security-specific automated tests. Do not run on clinical systems.

## 2. Encrypt an *exported de-identified* waveform case

Inside your VIGIL folder using CMD (change the workspace path if needed):

```cmd
.venv\Scripts\python.exe scripts\research_safety_tools.py list-case-ids
.venv\Scripts\python.exe scripts\research_safety_tools.py encrypt-case --case-id YOUR_CASE_ID --output "D:\ApprovedResearch\synthetic_case.ve1"
.venv\Scripts\python.exe scripts\research_safety_tools.py inspect-encrypted --file "D:\ApprovedResearch\synthetic_case.ve1"
```

Choose a unique long passphrase. Typing does not echo. The operator must store/recover the passphrase securely; **there is no recovery/reset tool**. The tool creates a new encrypted file only. It never overwrites an existing export. Original NPZ and SQLite files remain as they were. Do not import identifying fields; the header screening is incomplete and cannot assure de-identification.

## 3. Anchor the local audit trail outside the writable workspace

Create a separate, protected external folder (preferably on a disconnected/managed drive; here `E:\VIGIL_Audit_Evidence`). Back it up using approved institutional procedures.

```cmd
.venv\Scripts\python.exe scripts\research_safety_tools.py create-audit-key --key-path "E:\VIGIL_Audit_Evidence\audit.key"
.venv\Scripts\python.exe scripts\research_safety_tools.py seal-audit --key-path "E:\VIGIL_Audit_Evidence\audit.key" --output "E:\VIGIL_Audit_Evidence\anchor_001.json"
.venv\Scripts\python.exe scripts\research_safety_tools.py verify-audit --key-path "E:\VIGIL_Audit_Evidence\audit.key" --anchor "E:\VIGIL_Audit_Evidence\anchor_001.json"
```

Preserve both the key and sealed anchor, with restricted access. A compromised account that can alter the workspace, external key *and* anchor can still forge history. Subsequent audit events do not invalidate prior sealed prefixes, but deletions or rewritten history are detected against the retained anchor.

To add an anchor result to the readiness report:

```cmd
.venv\Scripts\python.exe scripts\hospital_readiness_check.py --audit-key "E:\VIGIL_Audit_Evidence\audit.key" --audit-anchor "E:\VIGIL_Audit_Evidence\anchor_001.json" --output "readiness_runs\NEW_CHECK_001"
```

## 4. Generate engineering evidence without raw data

Double-click `RUN_ENGINEERING_EVIDENCE_WINDOWS.bat`; it reruns tests and records the source hash and dependency versions in a new folder. Never call this a clinically validated, licensed, secure-hospital release.

## 5. Missing for future hospital use

A managed clinical security system requires per-user identity (hospital SSO, MFA), server-side authorization, RBAC, encryption at rest of entire storage including backups and exports, independently managed keys, SIEM logging, security operations, vetted third-party dependencies, backup restoration and red-team/penetration testing. None is claimed here.
