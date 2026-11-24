# Dataset catalog and access rules (2026-11-24)

**No real clinical dataset is redistributed in this repository.** All files inside `examples/` with synthetic in their names are programmatic fixtures. A downloader for one openly distributed WFDB source is provided but does not run automatically.

| Source | Modalities | Access | Recommended use |
|---|---|---|---|
| [MIT-BIH Arrhythmia Database](https://physionet.org/content/mitdb/1.0.0/) | two-lead ECG; expert annotation `.atr` | open, ODC Attribution 1.0 | ECG import tests, QRS matching, signal-quality study |
| [PhysioNet/CinC 2015 Critical Alarm](https://physionet.org/content/challenge-2015/1.0.0/) | ECG, PPG and/or ABP; alarm labels | review specific dataset terms | independent ICU false-alarm methods research (not automated suppression) |
| [Surface EMG walking v1.0.1](https://physionet.org/content/semg/1.0.1/) | EMG | open, check source license | RMS, median frequency and time-frequency descriptors |
| [Ninapro](https://ninapro.hevs.ch/) | sEMG, kinematic / other modalities | check per-dataset permissions; no redistributing without rights | prosthetic EMG movement studies |
| [TUH EEG Corpus](https://isip.piconepress.com/projects/nedc/html/tuh_eeg/) | EEG, expert event datasets | requires formal dataset access request | EEG spectral and event-quality research |
| [MIMIC-IV Waveform](https://physionet.org/content/?topic=mimic-iv) | ICU waveforms | **credentialed**; signed DUA / training | independent observational ICU validation |

## Provenance checklist

1. Capture dataset name, exact version, DOI, original license and download date.
2. Save source hashes and all preprocessing settings; prohibit patient identifiers in published exports.
3. Preserve the original labels separately. Never relabel as a medical diagnosis based on a heuristic.
4. Split by independently identified patient / device / hospital when appropriate. Never mix segments from the same patient across train and held-out test.
5. Publish only data and derived results allowed by the dataset's license and any data-use agreement.

### Direct MIT-BIH sample acquisition

```
python scripts/download_physionet.py --records 100 101 102 103 --out external_data/mitdb
```

This downloads files only when explicitly invoked. The script records URL, SHA256 and source metadata. It is not a background dataset loader. A failure to connect should be reported, not replaced with invented recordings.
