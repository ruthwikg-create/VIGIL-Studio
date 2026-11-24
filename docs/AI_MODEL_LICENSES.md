# External model dependency and research boundaries

## Optional open-weight foundation model

- Publisher: Auton Lab, Carnegie Mellon University.
- Repository: https://huggingface.co/AutonLab/MOMENT-1-large
- Paper: Goswami et al., MOMENT: A Family of Open Time-series Foundation Models, ICML 2024. https://arxiv.org/abs/2402.03885
- Metadata: MIT license (verify again before download/redistribution).
- File: `model.safetensors` (1385501256 bytes, about 1.39 GB decimal).
- Expected SHA-256: `a56928052ac6f5d09b97c3834bea6ce3aef9f02b513b5fac98954e7377801572` as surfaced on upstream file page on 24 Nov 2026.
- Version pin: `3582f9d7f033eea9d43e6a802ba0e36d5f26b57c` (known safetensors commit).
- The model was NOT downloaded or executed in our network-restricted build environment. Any embeddings obtained on the user's machine require validation before interpretation. It is a GENERAL time-series foundation model, not a clinically validated diagnostic model.
- Source and weights are provided by the upstream publisher; NO third-party weights are in this source release. See upstream licensing, security, use restrictions, and attribution.
- Local model acquisition requires an explicit `--accept-license` action; the file size and SHA-256 must match before any computation.

## Local CNN model

- Randomly initialized, trainable 1D ResNet-style convolutional network.
- Requires **independently labelled real data** to create a research-specific model; the program does not invent labels.
- Uses safe `safetensors` format, full local model card, group-disjoint train/validation/test, validation temperature calibration, post-hoc held-out metrics and modality-stratified results.
- Any result measured on synthetic test fixtures is an ENGINEERING TEST only and is never presented as clinical performance.

## Environment disk use

PyTorch, native libraries, the original VIGIL signal libraries, optional MOMENT package and a 1.39 GB foundation checkpoint can occupy approximately 2–5 GB depending on platform, CPU vs GPU wheels and Python environment. Disk use is not guaranteed or a quality metric. No 1–5 GB archive was produced in this offline environment. Windows native EXE remains unverified here.
