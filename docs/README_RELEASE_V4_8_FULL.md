# VIGIL Studio v4.8 — Professional Research Reporting

**Current intended use: offline research with de-identified biomedical waveforms only.** Engineering tests and report styles do not establish clinical device approval, hospital operational readiness or permission for patient care.

## New in v4.8

- **Evidence Studio** replaces the generic Reports & Exports list with a designed scientific reporting workspace. It includes responsive layouts, separate document/data/sharing categories, and a package integrity verification action.
- **Redesigned research PDFs**: four-section A4 waveform dossier, with the approved VIGIL signal logo, typography, multipanel plots, sampling details, analytical provenance and scientific limitations.
- **Professional supplementary PDFs**: hospital engineering-readiness status and fixed-protocol ECG validation now export as styled PDFs beside their original JSON/CSV/Markdown evidence.
- **Controlled ZIP evidence bundle**: offline HTML index, styled dossier PDF, machine-readable exports, scientific data dictionary, README and SHA-256 manifest. ZIP verification detects changed/missing/extra files without extracting them. It is **not** a signature or a hospital compliance attestation.
- **MIT-BIH expert annotation inventory**: optional standalone PDF from a reference CSV; clearly distinct from machine predictions.
- **No changes to the 14-section research workstation or to its approved pulse logo.** Existing source and case storage remain compatible. 

See **[Professional reporting guide](docs/PROFESSIONAL_REPORTING_V4_8.md)** and the actual sample exports in `examples`.

## Run on Windows

1. Back up the existing `VIGILStudio_Workspace` research folder; extract this release to a new folder.
2. Double-click `START_WINDOWS.bat` (Python 3.12 is recommended; the launcher installs dependencies if needed).
3. Open a research case and go to **10 Reports & Exports**.
4. Generate the PDF research dossier and evidence package; use **VERIFY EXPORTED ZIP** to check its internal manifest.
5. For the detailed readiness PDF, run `RUN_HOSPITAL_READINESS_CHECK_WINDOWS.bat`; for ECG benchmark PDF, use `RUN_MITBIH_VERIFICATION_WINDOWS.bat` on the original MIT-BIH `.hea/.dat/.atr` files.
6. For an MIT-BIH annotation-label PDF from the existing CSV, run `GENERATE_REFERENCE_REPORT_WINDOWS.bat`.

**Technical verification:** `RUN_SELF_TEST_WINDOWS.bat`. The last validated release results are in `TEST_RESULTS.md`. Windows rendering and actual 48-record ECG metrics must be verified on the user's PC.

---

# VIGIL Studio v4.7 — Research Safety Engineering Release

**Clinical release is BLOCKED.** This is a tested research-workstation upgrade, **not** an authorized hospital patient-care system. It does not provide clinical diagnosis, patient monitoring, alarm control, a hospital EHR connection, or validated diagnostic AI.

**Start here:** [`docs/READ_ME_FIRST_HOSPITAL_PROJECT.md`](docs/READ_ME_FIRST_HOSPITAL_PROJECT.md). For the code review and standards-to-evidence assessment see [`docs/HOSPITAL_READINESS_ENGINEERING_V4_6.md`](docs/HOSPITAL_READINESS_ENGINEERING_V4_6.md), [`docs/SECURITY_THREAT_MODEL_V4_6.md`](docs/SECURITY_THREAT_MODEL_V4_6.md) and [`docs/REQUIREMENTS_TRACEABILITY_V4_6.csv`](docs/REQUIREMENTS_TRACEABILITY_V4_6.csv).

**Inherited v4.6 features:** saved-waveform SHA-256 verification for new records with safe legacy flags; NPZ archive preflight limits; normalized duplicate CSV channel rejection and expanded identifier-header checks; formula-safe CSV text; an in-app read-only safety button; an offline structured readiness-report generator and 118 automated tests. The previously approved logo, all 14 desktop sections, ECG validation, and the Windows launcher are retained.

**Windows:** extract into a separate directory (backup old workspace first); run `START_WINDOWS.bat`, then `RUN_SELF_TEST_WINDOWS.bat` and `RUN_HOSPITAL_READINESS_CHECK_WINDOWS.bat`. These are engineering/research tests only. The large published datasets and optional AI foundation weights remain separate downloads.

---

# VIGIL Studio v4.4 — User-Selected Signal Logo & Brand Identity

**Windows-oriented native desktop application + genuine large public biomedical dataset manager + classical / trainable neural / optional pretrained foundation model research engines.**

> **RESEARCH ONLY.** Not a clinical monitoring system, alarm suppressor, medical device, diagnostic model or replacement for qualified clinical judgment. No human clinical trial, medical-grade regulatory assessment or patient-safety performance assessment was performed. Screenshots and test fixtures are explicitly synthetic.

![Layout-corrected Instrument Workbench](examples/LAYOUT_WORKBENCH_V4_3.png)

![Signal Lab screenshot](examples/SIGNAL_LAB_V4.png)

![ECG reference validation (SYNTHETIC engineering test)](examples/ECG_VALIDATION_V4_1_SYNTHETIC.png)

## New in v4.4: your approved original logo is integrated

- Uses the **exact uploaded VIGIL STUDIO pulse-and-frame artwork**, resized carefully for the sidebar and Windows application icon. No letter logo, shield, or leaf was introduced.
- Replaces the default Tk feather with a real waveform `.ico` and `.png` window icon.
- Title bar: `VIGIL Studio 4.4 | Instrument Workbench | Developed By Ruthwik Goparaju`.
- Adds `Developed By Ruthwik Goparaju` to the lower workspace footer, while retaining research-use safety notes in the sidebar.
- Changes Windows `.exe` build scripts to bundle brand assets and specify the supplied icon.
- Preserves all 14 sections, case and annotation persistence, and 9–18 pt sidebar adjustment.
- Original upload is retained at `vigil_studio/assets/vigil_full_logo_original.png`.

See `docs/BRAND_IDENTITY_V4_4.md` and `examples/BRAND_V4_4_*.png` for tested interface views.

## New in v4.3: visible workbench issues corrected

- **01–14 now appear in numerical order**; ECG Validation (13) follows Guide & Safety (12), and Settings (14) follows ECG Validation.
- Wider, scrollable navigation that accommodates 9–18 pt sidebar fonts without covering the main workspace.
- Layout adapts to narrower displays without crushing the central waveform plot; the extra right inspector is hidden when needed.
- Source Library controls stay visible at laptop-height windows; toolbar badges make space for actions when width is constrained.
- Settings, ECG and overview explanatory text wraps rather than being clipped.
- Scientific modules, stored cases and annotation database format remain unchanged.

See [the visual regression notes](docs/LAYOUT_FIXES_V4_3.md), the [1650×900 screenshot](examples/LAYOUT_WORKBENCH_V4_3.png) and [1120×720/18-pt screenshot](examples/LAYOUT_NARROW_V4_3.png).

## Inherited from v4.2: sidebar text accessibility

- **14 Settings** page and always-accessible **SETTINGS** toolbar button.
- Live **9–18 pt** sidebar typography slider with larger 11-pt default, automatic horizontal resizing and scrollable navigation.
- Automatic saved preference survives restart; **RESET SIZE** restores the default.
- Local settings are stored in `%APPDATA%\VIGILStudio\settings.json` on Windows, separate from case and annotation records.
- All existing ECG Validation, AI Research and other modules are retained, and the data storage schema is unchanged.
- [Accessibility setup guide](docs/SIDEBAR_ACCESSIBILITY_V4_2.md)

![Settings with larger sidebar text](examples/SETTINGS_V4_2.png)

## Inherited from v4.1: native MIT-BIH ECG comparison

- An ECG Validation research screen imports original WFDB `.hea` + `.dat` + `.atr` files, overlays publisher-supplied beat markers, runs an independent heuristic peak detector and reports one-to-one timing metrics.
- Complete MIT-BIH Record 100 (approximately 1,805.6 seconds at 360 Hz) is now eligible for direct import; the v4 WFDB import default silently stopped at 300 seconds. An 8-million-sample safety cap remains.
- Standalone repeatable benchmark command and auditable JSON/event-level CSV output. See **[the step-by-step guide](docs/ECG_REFERENCE_VALIDATION_V4_1.md)**.
- These features do **not** predict arrhythmia class or constitute medically validated QRS detection.

## What is actually delivered

This ZIP is a **complete testable source-code release of the research workstation** plus automated setup tools, not a pre-populated 30 GB portable installation. It contains:

- **Fourteen desktop sections:** Overview, Signal Lab, Quality Explorer, Modality Lab, Annotation Studio, ECG Validation, AI Experiments, Deep Learning Lab, Foundation Models, Research Environment, Reports & Exports, Audit Trail, Guide & Safety, Settings.
- Offline CSV, WFDB (optional via `wfdb`), EDF/BDF (`mne`) and local NPZ handling.
- Scientific ECG, EEG, EMG, PPG, ABP and respiratory waveform visualization, filters, descriptive time/frequency features and window-by-window exploratory quality metrics.
- SQLite case library, local review and annotated interval export, provenance and local hash-chain event log, research PDF/CSV/JSON exports.
- Transparent group-aware logistic quality baseline, trainable 1D PyTorch convolutional network with held-out group test evaluation, safe `safetensors` weights and experiment records.
- Optional **MOMENT-1-large 1.3855 GB general time-series foundation model**, fixed upstream model revision and SHA-256 verification. Model must be downloaded and separately runtime-tested on your computer.
- Ten official, publicly accessible, version-pinned biomedical dataset acquisition recipes spanning ECG, EEG, EMG, polysomnography, PPG and respiration. File integrity/ZIP/path checks, disk safety, resumable download, provenance receipts, WFDB header-only indexing and source checksum verification.
- Seeded signal-artifact stress laboratory, explicit research-only results.
- Native Windows AI `.exe` build script and regular desktop build script. The **built EXE was not produced or validated in the current Linux environment**.

## How to test the software on Windows, right now

You need Python 3.11 or 3.12 (x64) and internet access to install dependencies.

1. Extract the release ZIP to a user-writable folder such as `D:\VIGIL_Studio_v4_4`.
2. Double-click **`START_WINDOWS.bat`** for the base scientific desktop installation (the app uses locally installed Python libraries).
3. From the application, click **SYNTHETIC TEST** in the top instrument toolbar to test waveform plots, then visit the Quality Explorer, Modality Lab and Research Environment pages.
4. Double-click **`RUN_SELF_TEST_WINDOWS.bat`** once dependencies are installed. It checks the automated suite, safe environment catalog, and a synthetic artifact stress test.
5. For the advanced AI dependencies and large real datasets, follow the next section.

The base software can work with de-identified local recordings and synthetic fixtures without downloaded big data or a foundation model. The first setup requires internet for Python package downloads.

## Install the genuine 10–50 GB-class environment

Double-click **`INSTALL_FULL_RESEARCH_WINDOWS.bat`**. It will:

1. Check Python 3.11 and create a virtual environment with real NumPy, SciPy, Matplotlib, WFDB/MNE, scikit-learn, PyTorch, `momentfm`, `safetensors`, and Hugging Face client dependencies.
2. Ask for your desired storage drive, for example `D:\VIGIL_Research_Data`. Your selection is saved in a local launch configuration; do not store protected clinical records without an appropriate security environment.
3. Run the automated source tests and print the source/version/size installation plan.
4. Require that you review the original dataset/model licenses and **type `DOWNLOAD`** before any large asset acquisition.
5. Attempt the official **29.03 GB unpacked** public multimodal collection (about 20.08 GB in archive downloads). Archives are downloaded sequentially, validated and unpacked; the installed dataset collection is independent of the source ZIP.
6. Attempt the approximately **1.3855 GB MOMENT-1-large** weights from its official publisher, validating size and SHA-256.
7. Save a local `environment_snapshot.json` with which sources installed and actual disk/model status, then open the desktop application.

**You should have at least 50 GB free**, preferably more, on the chosen drive. The model also needs enough RAM or VRAM to run. High-volume clinical datasets may require institutional access; **only the ten listed public datasets** are included in this install plan, and none are forced onto the device.

There is no hidden simulated medical dataset, no fake 10GB padded file, and no model weights bundled in the source ZIP. A network error, insufficient space, model incompatibility or repository availability issue can prevent completion on your own machine. **A successful ZIP download alone does not prove medical-data correctness**; the receipt and index/checksum commands are for further verification.

For a smaller ECG-only collection (~16.9 GB, unpacked) or to install one source at a time:

```powershell
.\.venv\Scripts\python.exe -m vigil_studio.environment plan --preset research-10gb
.\.venv\Scripts\python.exe -m vigil_studio.environment install ptb-xl --accept-license
.\.venv\Scripts\python.exe -m vigil_studio.environment index ptb-xl
.\.venv\Scripts\python.exe -m vigil_studio.environment verify-source ptb-xl
```

To view the optional model status and install separately after reviewing its license:

```powershell
.\.venv\Scripts\python.exe -m vigil_studio.ai model-status
.\.venv\Scripts\python.exe -m vigil_studio.ai download-moment --accept-license
```

If you installed to a custom workspace through the Windows setup, run the subsequent commands with:

```powershell
.\.venv\Scripts\python.exe -m vigil_studio.environment --workspace "D:\VIGIL_Research_Data" status
.\.venv\Scripts\python.exe -m vigil_studio.ai --workspace "D:\VIGIL_Research_Data" model-status
```

## Build Windows executables

- `scripts\BUILD_WINDOWS_EXE.bat`: normal native desktop distribution without the large PyTorch/model ecosystem.
- **`scripts\BUILD_ADVANCED_AI_WINDOWS_EXE.bat`**: advanced AI native one-folder executable distribution with actual PyTorch/MOMENT/scientific libraries. Output: `dist\VIGILStudioAI\VIGILStudioAI.exe` **on Windows after the build passes**.

All dependencies need to remain next to the corresponding `.exe` in the `dist` directory. This repository cannot ship a precompiled or code-signed Windows EXE because it was developed and tested in a Linux container. A GitHub Actions Windows workflow for the basic distribution is included, but it is not represented as executed.

## Research tasks and outputs

**Classical ML:** independently human-labelled quality windows, group-held-out logistic baseline, JSON research model.

**Deep-learning ML:** 1D waveform neural model, group-separated train/validation/test, temperature scaling chosen on validation, AUROC/Brier/ECE/balanced accuracy/confusion matrix/group bootstrap and model cards. Metrics on the included synthetic test data are not clinical evidence.

**Pretrained foundation embeddings:** fixed 512-sample normalized windows through MOMENT, producing `.npz` research embeddings after the genuine checkpoint is downloaded and verified. This adapter has not been tested with those weights in the source environment.

**Signal stress tests:** controlled baseline wander, 50/60 Hz interference, dropout, flatline, gain and motion-burst perturbations with a reproducible seed. Perturbation flags are **not real human clinical labels**.

**Large data:** version-pinned public datasets with source/license/DOI receipts, safe extraction, metadata-only WFDB index, opt-in SHA256SUMS verification, exact workspace disk inventory. EEG EDF files use the EDF/BDF importer rather than WFDB index.

## Command-line quick reference

```text
python -m vigil_studio.environment catalog
python -m vigil_studio.environment plan --preset research-multimodal-30gb
python -m vigil_studio.environment status
python -m vigil_studio.environment install mitdb --accept-license
python -m vigil_studio.environment install-preset --preset research-multimodal-30gb --accept-licenses --continue-on-error
python -m vigil_studio.environment index mitdb
python -m vigil_studio.environment inventory mitdb
python -m vigil_studio.environment verify-source mitdb
python -m vigil_studio.environment stress-test examples/synthetic_agreement.csv --channel ECG --out stress.json
python -m vigil_studio.environment snapshot --out environment_snapshot.json
python -m vigil_studio.ai validate independently_reviewed_manifest.csv
python -m vigil_studio.ai train independently_reviewed_manifest.csv --out runs/quality_trial_001 --epochs 20
python -m vigil_studio.ai model-status
```

## Evidence and restrictions

- Tests: **72 automated checks passed** on Linux/Python 3.13, including an actual PyTorch training/export/inference test on generated fixtures, safe ZIP extraction from local fixtures, source inventory and data integrity tests. The native GUI was smoke-tested separately.
- GUI: All 12 pages were rendered under Linux/Xvfb; see `examples/ENVIRONMENT_SCREENSHOT.png`.
- The source was **not** tested against a downloaded hospital dataset, the large MOMENT checkpoint or Windows executable in this environment. Public data and model servers were unavailable for bulk downloads.
- No encryption-at-rest, authenticated clinical user management, hospital integration, medical-device QMS, penetration test, external clinical validation, published clinical results or regulatory authorization is provided.

For full scientific boundaries and official attribution, consult:

- `docs/DATA_SOURCES_AND_LICENSES.md`
- `docs/AI_ENGINES_AND_EXPERIMENTS.md`
- `docs/RELEASE_SCOPE_V3.md`
- `docs/SECURITY_AND_REGULATORY.md`
- `docs/VALIDATION_ROADMAP.md`

**Medical-grade software is established by controlled development, risk management and empirical clinical evidence, not by download size.**

## v4 user-interface architecture
The v4 redesign is a full shell and primary-workspace replacement, not a recoloured dashboard: a scientific acquisition workbench, three-pane draggable signal lab, compact tool navigation, measurement typography, cursor readout and per-modality trace palette. Other specialty tools remain accessible and retain their v3 research behavior. See `docs/INSTRUMENT_DESIGN.md` and `examples/WORKBENCH_V4.png`.

The distributable is source code with Windows launch/build scripts; Windows `.exe`, pretrained weights and multi-gigabyte data are still NOT bundled or clinically validated.

## Additional 2026-11-24 clinical-readiness verification toolkit (research only)

The packaged v4.4 workstation now includes an **independent batch ECG reference-location evaluation workflow**. There is no change to the approved signal logo or existing interface. See `docs/VALIDATION_INSTRUCTIONS_WINDOWS.md` and run `RUN_MITBIH_VERIFICATION_WINDOWS.bat` with your original local MIT-BIH `.hea`, `.dat`, `.atr` files. The original detector and its thresholds are deliberately unchanged.

The toolkit records SHA-256 source hashes, fixed 150ms position-matching protocol, per-record TP/FP/FN, sensitivity/PPV/F1 and timing errors. It reports failed or missing records as incomplete, does not silently discard hard cases, and does not classify arrhythmia or demonstrate medical-device authorization. See `docs/CLINICAL_READINESS_GATE_1.md` and the draft risk/traceability registers for explicit unresolved clinical hazards and evidence gaps.

## v4.7 — Research safety engineering (NOT hospital authorization)

Adds authenticated encrypted **research case exports** (`requirements-security.txt`), externally anchored local audit snapshots, bounded CSV ingestion, explicit warnings on raw/ZIP exports, and repeatable engineering evidence capture. The original research workspace remains **unencrypted and single-user**. No hospital role management, live patient monitoring, regulatory clearance or clinical validation exists. **CLINICAL DEPLOYMENT IS STILL BLOCKED.**

- `RUN_SECURITY_TESTS_WINDOWS.bat` — install optional crypto and run targeted negative-condition tests.
- `scripts/research_safety_tools.py --help` — create a research encrypted handoff or independent audit anchor (no GUI clinical login).
- `RUN_ENGINEERING_EVIDENCE_WINDOWS.bat` — run test/evidence snapshot with local code hashes and environment inventory.
- `docs/RESEARCH_SECURITY_OPERATIONS_V4_7.md` — exact Windows usage and safety cautions.
- `docs/HOSPITAL_DEPLOYMENT_BLOCKERS_V4_7.md` — requirements that cannot be closed without a hospital sponsor, independent validation, QMS and regulatory review.

Keep v4.6 as a backup and verify actual Windows operation before treating new features as tested on that platform. No installed hospital project should use real identifiable patient data in this research edition.
