# VIGIL Studio v4.8

**Biomedical Signal Analysis & AI Research Workstation**  
**Developed by Ruthwik Goparaju**

> **Research and engineering use only.** VIGIL Studio is not clinically validated or authorized for patient diagnosis, bedside monitoring, clinical alarms, or treatment decisions.

VIGIL Studio is a Python desktop research environment for exploring physiological signals, analyzing recording quality, developing biomedical AI workflows, evaluating ECG detectors with reference annotations, and producing reproducible scientific reports.

## Key features

- ECG, EEG, EMG, PPG, arterial blood-pressure, and respiration waveform analysis
- Interactive signal visualization, filtering, quality indicators, and artifact investigation
- WFDB / MIT-BIH research workflows, reference-label overlays, and QRS timing evaluation
- Human annotation tools, case management, research audit history, and scientific reports
- Classical machine learning, PyTorch experiments, and optional foundation-model integration
- Adjustable desktop navigation, original VIGIL signal logo, and Windows launch scripts

## Local project release

The prepared **v4.8 source and showcase package** includes 157 source, documentation, test, and selected screenshot files. The complete GitHub-ready ZIP was prepared and tested separately; the full source upload is still pending.

Once uploaded, run `START_WINDOWS.bat` on Windows with Python 3.12. For synthetic demonstration cases use `START_SHOWCASE_WINDOWS.bat`.

## Testing and claims

The prepared v4.8 project passed **126/126 local automated tests**. These are software engineering checks, **not** clinical diagnostic accuracy measurements or proof of regulatory compliance.

The MIT-BIH Arrhythmia Database is available from [PhysioNet](https://physionet.org/content/mitdb/1.0.0/). Private hospital records, local research databases, AI weights, and large datasets must not be committed to a public repository.

## Ownership and safety

Do not publicly commit patient-identifiable data, credentials, encryption keys, or confidential hospital materials. Verify the right to publish commissioned code before using it in an institutional context.

**Clinical deployment status:** Not established. Research software only.

**License:** MIT for VIGIL Studio source (third-party datasets, dependencies and models have separate terms).
