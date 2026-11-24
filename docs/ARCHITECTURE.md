# VIGIL Studio v3 — software architecture

## Deployment

Local single-user Python desktop research workstation with a native Tk GUI and Matplotlib signal plots. Workspaces contain source datasets, header indexes, experiment outputs, model weights, human annotations and SQLite case records. No cloud service, telemetry or live hospital monitor control is provided.

```text
Native desktop (12 pages) / reproducible CLI
 |-- Waveform Lab: CSV / NPZ / optional WFDB / EDF-BDF
 |-- Signal analysis: ECG, EEG, EMG, ABP, PPG, respiration
 |-- Signal quality timeline, comparison, robustness stress lab
 |-- Case database, human-labelled intervals, reports and audit chain
 |-- Classical grouped evaluation / optional abstention logic
 |-- PyTorch 1D CNN: group-disjoint train/validation/test
 |      |-- calibration, test metrics, training metadata and model card
 |      `-- safetensors weights and inference
 |-- Optional MOMENT-1-large: upstream SHA-256 verified time-series model
 `-- Research environment: 10 version-pinned real data sources
        |-- official HTTPS downloads / local archive import
        |-- license consent, resume, guarded staging + ZIP extraction
        |-- sha256 receipt, optional publisher source checksum checks
        `-- WFDB metadata-only index, disk inventory, snapshots
```

## Scientific trust boundaries

1. Input waveforms and human annotation labels are research data, not proven clinical ground truth. Never infer the correctness of a clinical prediction from a synthetically generated signal.
2. The v3 downloader is explicit user-initiated HTTPS-to-local-storage. It does not download data simply by opening the UI or running tests. License acceptance is required before installs.
3. Group-disjoint machine-learning partitions reduce recording-level leakage but do not prevent all site, patient or demographic confounding. External clinical cohorts are still required.
4. Model weights are stored in `safetensors` rather than accepting arbitrary untrusted Python pickle checkpoints. This reduces deserialization risk, but does not guarantee model behavior.
5. Generated reports and software analytics are for research and human review. There is no autonomous alarm suppression, diagnostic reporting or treatment recommendation.
6. Installation and source checksum receipts are not substitutes for supplier provenance verification, clinical data governance, security assessment or regulatory QMS.

## Implementation interfaces

- `vigil_studio/ui/` — GUI and navigation.
- `vigil_studio/core/` — signal import, feature analysis, artifact scoring and modalities.
- `vigil_studio/ai/` — training, evaluation, `safetensors` and optional pretrained adapter.
- `vigil_studio/environment/` — curated dataset catalog, download/install/index/inventory and robustness tools.
- `vigil_studio/data/` — local records and reviewer annotation serialization.
- `vigil_studio/reports/` — PDF and structured research outputs.
- `tests/` — engineering fixtures and regression checks.
- `INSTALL_FULL_RESEARCH_WINDOWS.bat` — opt-in, interactive download and environment installation.
- `scripts/BUILD_ADVANCED_AI_WINDOWS_EXE.bat` — Windows-only PyInstaller recipe, unverified here.

See `docs/RELEASE_SCOPE_V3.md` for implementation-versus-validation boundaries and `docs/DATA_SOURCES_AND_LICENSES.md` for each upstream source/license.
