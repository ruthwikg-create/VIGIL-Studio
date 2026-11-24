# VIGIL Studio v3 — validation boundaries and known limitations

## Verified in the development environment

- The native 12-section Tk / Matplotlib desktop application starts under a Linux virtual display and navigates its sections.
- Automated research software tests cover input parsing, waveform features, analysis reports, local storage, annotation, audit history, evaluation, AI training, data licensing, dataset archive protection and metadata indexing.
- A genuine CPU PyTorch 1D CNN performs training, checkpoint save (safetensors), reload and inference on deliberately synthetic test fixtures. It has **not** demonstrated medical performance.
- The public dataset catalog and resumable safe installer have been exercised against local test ZIPs, not remotely downloaded full PhysioNet collections.
- An environment inventory, provenance receipt, disk check, WFDB header-only metadata index, optional upstream checksum comparison and seeded robustness-perturbation report are implemented and locally tested.

## Not delivered or verified

- **No 10–50 GB offline bundled archive**: large data and 1.39 GB model weights are not present in the source ZIP. Downloads on a network-connected computer may produce a genuine 30+ GB installation, depending on source accessibility and licenses.
- **No validated pretrained biomedical diagnosis model**: MOMENT-1-large is an optional general time-series foundation model. Its full checkpoint could not be retrieved or runtime-tested here.
- **No Windows .exe binary** was compiled, signed or executed here. Windows install scripts and a PyInstaller build recipe are included but require testing on Windows.
- **No real-world clinical ML benchmarks**: no real patient cohort was downloaded, processed or clinically evaluated in this environment. Scores on synthetic fixtures are engineering checks only.
- **No clinical trial, physician-led validation, ethics approval, regulatory authorization or medical-grade status.** The software must not direct care, suppress alarms or be used as a medical diagnosis.
- **No hospital interfaces**, live bedside-device integration, multi-user authentication or clinical compliance certification.
- No encryption of the SQLite case store at rest, no full de-identification assurance, no protected patient-data handling guarantee; use public or appropriately de-identified research data only.
- Large waveforms can exceed RAM, and importing substantial files through desktop plots can be slow. Bulk environment indexing is metadata-first rather than ingesting complete waveforms into memory.

## Integrity and clinical interpretation

- ZIP CRC checks, defensive path validation, and local SHA-256 receipts protect against some transfer and file-corruption problems; a local receipt alone does **not** prove the original publisher's identity. When available, use `verify-source` against official checksum files.
- Per-signal quality, EEG, ECG, EMG and respiratory descriptors are **exploratory**, with unvalidated thresholds; they are not medical-device algorithms.
- A local SQLite hash chain detects some accidental or direct data changes, but an attacker with complete filesystem access could replace both the database and chain. It is not a cryptographically signed clinical audit log.
- Dataset access, model download, storage and software installation require permissions, local network reachability and sufficient RAM/disk. The installer reports partial failure rather than marking downloads complete.

## Addendum for v4.1

- ECG `.atr` reference marks are supplied by PhysioNet, not predicted by the application.
- The new ECG detector is exploratory and class-agnostic. TP/FP/FN measure beat *location agreement*, not diagnostic accuracy or arrhythmia detection.
- Full native WFDB MIT-BIH Record 100 import is implemented but cannot be end-to-end checked against original `.dat` bytes here because those files were not uploaded. This must be tested on the user's Windows computer.
- Importing a full recording can take appreciable RAM and CPU. Do not run this on live patient systems.
