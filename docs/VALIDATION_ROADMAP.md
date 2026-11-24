# Research validation and clinical-translation gates

This document sets out proposed work. **No phase beyond the software integration test has been completed.**

## Gate A — Functional software assurance (research-only)

- Import property tests, truncation/oversized file checks, provenance/source hashing, numeric stability and missingness behavior.
- Repeatability across supported Python versions and operating systems.
- Windows executable build, functional smoke tests, packaging verification and malware/security review.
- Review synthetic fixtures ONLY for code correctness. Zero claims of clinical accuracy from fixtures.

## Gate B — Fixed retrospective research benchmark

- Protocol registration before viewing independent held-out labels.
- Define reference dataset: MIT-BIH for beat annotation and PhysioNet/CinC 2015 for ICU alarm context; match input waveform channels and annotation type.
- Separate expert beat detection, signal-quality classification, alarm classification and actual patient outcomes. These are **distinct scientific problems**.
- Predefine allowable missingness, sensor units, channel mapping, preprocessing and all thresholds.
- Assess precision/recall/F1 and detection timing for beat annotation; AUROC, sensitivity, specificity, Brier, calibration and abstention for quality labels; predefine clinical harm metrics for any alarm proposal.
- External validation by patient/site/device with confidence intervals and worst-subgroup analysis.
- Compare against fixed single-modality, classical ML and published baseline methods; use confidence intervals and ablations.
- Reproduce results with a locked environment, fixed random seeds and full manifest of data provenance.

## Gate C — Multicentre silent-mode research

- Hospital collaborator and independent clinical principal investigator.
- Ethics committee approval where needed, research agreements, secured access and consent/privacy arrangements.
- Device interface with manufacturer-approved protocols and network safety review; strict isolation from clinical alarms.
- Output is logged **silently**; care is never changed based on experimental analysis.
- Prospective benchmark includes timestamp alignment, packet loss, lead-off, transfer between wards, differing monitor brands and peak-time shifts.

## Gate D — Clinical software governance

- Intended use, software safety classification and validated design inputs.
- Quality management, requirements traceability, hazard/risk analysis, verification/validation, usability, cybersecurity testing, incident handling and post-market monitoring plan.
- Applicable local regulatory authorization and clinical investigation controls before interventional use.
- Professional clinical collaborators, independent adjudicators and external statisticians to design and evaluate any intervention study.
- Clinical benefit demonstrated in meaningful clinician/health outcome endpoints. A model accuracy score by itself is insufficient.

## Novelty hypothesis (not established)

An uncertainty-aware, *human-reviewed*, multimodal signal-integrity assessment with explicit abstention and external device/site evaluation may improve reliability of segment-quality classification under missing data and domain shift. This is a **research hypothesis**, not proof. Original alarm-reduction work already exists; any submission must compare fairly against prior art, preregister analyses and avoid claims of novelty from merely integrating ECG/PPG/ABP.

**Stop condition:** No automatic alarms muted, delayed, dismissed or downgraded by this system. This function is intentionally not part of the research build.
