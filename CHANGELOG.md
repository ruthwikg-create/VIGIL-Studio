# VIGIL Studio v4.8 — Evidence Studio & Professional Research PDFs (24 November 2026)

- Replaced the generic Reports & Exports layout with a responsive instrument-style Evidence Studio screen; added direct PDF generation, evidence package export and ZIP verification actions.
- Rebuilt waveform case reports as a structured multi-page research dossier containing original waveform previews, channel metrics, windowed quality trends, provenance, reviewer records and limitations.
- Added professional PDF outputs to retrospective ECG benchmark and hospital-readiness assessments, keeping the machine-readable JSON, CSV and Markdown outputs.
- Created an independent published reference annotation inventory report, clearly separating expert labels from detector results.
- Added offline HTML evidence index, controlled export manifest and read-only ZIP consistency verifier, with checks for altered, missing and unexpected files.
- Preserved the user-approved signal logo, sidebar accessibility, 14 desktop pages, waveform pipeline, and clinical release block. No clinical authorization or live bedside features are claimed.

---

# VIGIL Studio v4.7 — Research Safety Engineering (24 November 2026)

- Added optional authenticated AES-GCM encrypted exports for de-identified research waveform NPZ files. Original workspace and database **remain unencrypted**.
- Added off-workspace HMAC audit-history anchoring and verification, with fail-closed tamper/truncation detection. This is not tamper-proof institutional logging.
- Added optional CLI to inspect encrypted research case metadata without writing raw decompressed data to disk.
- Added a bounded CSV cell-count import guard against some resource-exhaustion failures.
- Added confirmations before exporting raw waveform CSV or unencrypted case ZIP bundles.
- Expanded Guide & Safety with research security instructions and a security-status section in readiness output.
- Added local source-hash/dependency/test evidence collector, security operations guide, and explicit hospital gate blockers.
- Added 13 further engineering checks for encryption/anchor/evidence/fail-closed operations (118 total regression tests).
- Not tested against real patient datasets or a hospital system. Clinical release remains **BLOCKED**.

---

# VIGIL Studio v4.6 — Safety, Integrity and Hospital Readiness Engineering (24 November 2026)

- Added stored waveform SHA-256 checks for new cases, with fail-closed loading of altered archives and unverified-legacy status for old cases.
- Added NPZ archive preflight checks against hostile metadata/oversized decompression declarations.
- Rejected normalized CSV channel collisions and additional explicit personal-identifier columns.
- Escaped formula-like content in selected CSV exports.
- Added an in-app Guide & Safety integrity check and an independent `hospital_readiness_check.py` CLI with immutable-new-folder readiness reports.
- Added traceability, clinical sponsor intake, source code audit, security threat model and standards mapping documents.
- 105 software tests pass, graphical launch/navigation across 14 sections verified under a test display; genuine clinical validation not performed.
- Hospital clinical use remains explicitly blocked. No new diagnostic or live-monitor controls added.

---

# VIGIL Studio v4.4 — User-Approved Signal Logo

- Replaced V / sidebar text emblem with the waveform/frame mark cropped from the provided transparent image.
- Replaced default Tk feather via app icon PNG and multi-resolution Windows ICO.
- Title-bar credit and in-app footer: Developed By Ruthwik Goparaju.
- Bundled image assets in both Windows PyInstaller build paths.
- Preserved native workstation workflow, case database, model training, and existing validations.

# VIGIL Studio v4.3 — Navigation & Workspace Layout Fixes (2026-11-24)

- Ordered all 14 navigation items sequentially, moving **13 ECG Validation** after **12 Guide & Safety** and before **14 Settings**.
- Fixed side rail sizing and scrollbar visibility; ensure active destinations remain reachable at larger font sizes.
- Improved page-header separation, responsive toolbar actions and narrower-screen overview layout.
- Fixed hidden source-library action buttons and explanatory text clipped on narrower windows.
- Added automated navigation tests and screenshot-based graphical checks at multiple sizes and font settings.
- Preserved all previous research functions, case storage, annotation data and settings preferences.
- Research-only; not a medical-device validation release.

---

# VIGIL Studio v4.2 — Display & Accessibility Settings (2026-11-24)

- Added 14th navigation section, **Settings**, also accessible from the top toolbar.
- Adjustable left-sidebar font size, **9–18 pt**, with 11-pt default; live resizing and layout-aware sidebar width.
- Scrollable navigation for smaller screens and larger text; brand/footer/section labels scale appropriately.
- Automatic saved preferences under the user configuration directory, separate from biomedical records, with safe atomic file replacement and malformed-config handling.
- Added reset-to-default control, restored setting on application launch, and new accessibility tests and graphical screenshots.
- Preserved the v4.1 ECG Validation features and existing case/annotation workspace schema.
- Scientific disclaimer: visualization accessibility has changed, not medical-data processing or diagnostic validation.

---

# VIGIL Studio v4.1 — ECG Reference Validation (2026-11-24)

- Added thirteenth native workspace: ECG Validation, with reference `.atr` beat markers and independent signal-only predictions shown distinctly.
- Removed the default 300-second WFDB import limit; 8-million-sample-per-channel ceiling still applies.
- Added local waveform (header + `.dat`) hashes and `.atr` annotation checksum for research provenance.
- Added 1-to-1 event matching, TP/FP/FN, recall/sensitivity, PPV, F1, absolute timing errors, and exported event-level JSON/CSV.
- Added reproducible offline CLI `scripts/benchmark_mitbih.py`.
- Retained all existing v4 modules, existing workspace database format, and original instrument visual identity.
- Scientific warning: this is a beat-location benchmark with an unvalidated heuristic; NOT arrhythmia classification, clinical validation, or device certification.

---

# Changelog

## v4.0 — Instrument Workbench
- Replaced the v3 generic dark SaaS shell with an original instrument-first laboratory interface.
- Warm mineral and parchment research palette, copper focus colour and modality-specific trace ink.
- Consolidated 12 tools into three scientifically meaningful navigation groups; compact context header and instrument toolbar.
- Replaced the KPI-card overview with a three-pane acquisition workbench, case library, multi-trace plotting, and experiment inspector.
- Redesigned Signal Lab as a resizable three-pane viewer with per-channel metadata, filters and trace cursor.
- Added Ctrl+Left/Right span navigation, Ctrl+L case library, Ctrl+O import, Ctrl+R/F5 refresh, and Ctrl+1..9 navigation.
- Uses system fonts chosen by availability (Bahnschrift/Aptos or readable substitutes, and Consolas/mono); no font files are redistributed.
- Preserves all v3 dataset, ML, annotation, audit, import and export operations.
- UI is research-only; no clinical validation or Windows binary implied.

### Medical-device readiness verification supplement (24 November 2026)

- Added a fixed-protocol, reproducible **research-only** MIT-BIH beat-location batch benchmark (48-record dataset coverage when available locally).
- Added a Windows prompt launcher and per-record error/metrics/provenance exports.
- Added draft requirements traceability and clinical hazard risk registers plus explicit clinical readiness gates.
- Existing detector, UI, preferred logo and saved-workspace schemas remain unchanged.
- No medical-device certification or clinical performance is claimed.
