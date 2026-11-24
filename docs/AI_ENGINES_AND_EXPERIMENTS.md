# AI and scientific engines — exactly what is implemented

## Engine 1: Signal analytics, non-diagnostic

SciPy-powered offline filtering, time/frequency properties, and heuristic signal
quality descriptors for ECG, PPG, ABP, EEG, EMG and respiration. Time-series
visualization never suppresses alarms, treats disease or triggers patient actions.

## Engine 2: Transparent classical quality baseline

An inspectable standardized logistic-regression research baseline that uses
*independently annotated signal-quality labels*. Samples are separated by
independent group identifier. Saved coefficients use JSON rather than pickle.
This is not an arrhythmia classifier.

## Engine 3: Trainable 1D convolutional quality model

PyTorch waveform model with 512-sample normalized input; fixed random seeds;
group-disjoint train/validation/test; validation-only temperature calibration
and threshold selection; held-out AUROC, Brier, ECE, balanced accuracy and
confusion matrices; optional group-bootstrap AUC interval. Weights are stored
as `model.safetensors`; SHA-256 and architecture live in `model_card.json`.
**Only software tests on nonclinical synthetic data ran in this release.**

Train with **actual expert quality labels** after configuring a CSV manifest:

```text
path,group_id,label,channel,fs,start_s,modality
record100.hea,SUBJECT001,1,MLII,,0,ECG
record100.hea,SUBJECT001,0,MLII,,8,ECG
record101.hea,SUBJECT002,1,MLII,,0,ECG
```

The example above only illustrates the schema, **not real labels**. It should
never be used as a training dataset unless the values have been independently
verified by human reviewers. All paths must remain under the manifest folder.
The group_id must stay the same for all recordings from one subject.

```
python -m vigil_studio.ai validate path\to\approved_manifest.csv
python -m vigil_studio.ai train path\to\approved_manifest.csv --out runs\experiment_001 --epochs 25 --batch-size 32 --seed 42
```

## Engine 4: MOMENT-1-large pretrained *general* time-series model

**Upstream:** Auton Lab / Carnegie Mellon University, ICML 2024.
- Model: https://huggingface.co/AutonLab/MOMENT-1-large
- Paper: https://arxiv.org/abs/2402.03885
- Open-source code: https://github.com/moment-timeseries-foundation-model/moment
- License in upstream model repository: MIT (reverify before downloading)
- `model.safetensors`: 1,385,501,256 bytes
- File digest pinned in `vigil_studio/ai/registry.py`.
- The model is optionally downloaded to the designated local research workspace.
- The software rejects absent or integrity-mismatched weights.
- The `momentfm` embedding adapter is implemented but **was NOT runtime-tested
  against the downloaded checkpoint** because source build networking is blocked.
  Test on the target machine before using results even in a manuscript.

This model is **general-purpose**, not a medical-grade AI or a clinically
validated diagnostic system. Embeddings are research features only.

## Engine 5: Engineering robustness / data stress laboratory

A seeded, reproducible quality stress suite applies baseline drift, 50/60-Hz
interference, dropout, flatline, gain shifts and motion bursts to a local
waveform, then measures descriptor changes. This is **not** a benchmark of
clinical classification accuracy, as perturbations are not independent
physician-annotated truth. Use `Research Environment` CLI:

```
python -m vigil_studio.environment stress-test examples/synthetic_agreement.csv --channel ECG --out stress_report.json
```

## What makes a credible publication

1. Pre-register target use, task definition and hypotheses.
2. Obtain real, permissible, independently labelled data.
3. Conduct cross-subject AND cross-source/device holdout experiments.
4. Compare with an appropriately tuned classical baseline and fixed published methods.
5. Measure calibration, missingness, false reassurance, abstention, robustness
   under motion and electrical interference, and subgroup effects.
6. Do not reuse held-out recordings for model selection.
7. Independently review serious false-negative and uncertainty cases.
8. Release fully reproducible code/results where licenses allow.
9. In an actual clinical environment, proceed only under institutional governance,
   ethics review and applicable device/software regulatory requirements.

A novelty claim, clinical-trial pass or certification is **not** established by
an installation, a model's size, or passing unit tests.
