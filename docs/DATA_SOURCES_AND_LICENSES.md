# Official public research data and provenance

**No public waveform dataset is bundled with the downloadable source package.**
This environment performs **explicit**, per-dataset acquisitions from the following official
PhysioNet releases. The user must review the original license and conditions on the source page.
The pinned versions below were checked against the publishers' dataset pages on 24 Nov 2026.
Sizes are decimal GB and approximate; they do not include intermediate converted data.

| Modality | Source / pinned version | ZIP GB | Unpacked GB | License | Official source |
|---|---|---:|---:|---|---|
| ECG | MIT-BIH Arrhythmia 1.0.0 | 0.0735 | 0.1043 | ODC-By 1.0 | https://physionet.org/content/mitdb/1.0.0/ |
| ECG | MIT-BIH AF 1.0.0 | 0.4397 | 0.6059 | ODC-By 1.0 | https://physionet.org/content/afdb/1.0.0/ |
| ECG | MIT-BIH Normal Sinus 1.0.0 | 0.5827 | 0.5827 | ODC-By 1.0 | https://physionet.org/content/nsrdb/1.0.0/ |
| ECG | PTB-XL 1.0.3 | 1.7 | 3.0 | CC BY 4.0 | https://physionet.org/content/ptb-xl/1.0.3/ |
| ECG | Large-scale 12-lead arrhythmia 1.0.0 | 2.3 | 5.1 | CC BY 4.0 | https://physionet.org/content/ecg-arrhythmia/1.0.0/ |
| ECG | CinC Challenge 2020 1.0.2 | 4.5 | 7.5 | CC BY 4.0 | https://physionet.org/content/challenge-2020/1.0.2/ |
| EEG | EEG Motor Movement/Imagery 1.0.0 | 1.9 | 3.4 | ODC-By 1.0 | https://physionet.org/content/eegmmidb/1.0.0/ |
| Sleep / EEG | Sleep-EDF Expanded 1.0.0 | 8.1 | 8.1 | ODC-By 1.0 | https://physionet.org/content/sleep-edfx/1.0.0/ |
| PPG / Respiration | BIDMC PPG/Respiration 1.0.0 | 0.2078 | 0.2077 | ODC-By 1.0 | https://physionet.org/content/bidmc/1.0.0/ |
| EMG | Surface EMG Walking 1.0.0 | 0.2785 | 0.427 | ODC-By 1.0 | https://physionet.org/content/semg/1.0.0/ |

**Published dataset totals:** approx. **29.03 GB unpacked**, approx. **20.08 GB in ZIP downloads**.
These are not simultaneously needed on disk: each archive is unpacked and then its
partial-download archive is removed. However **the largest single dataset requires
substantial temporary storage**, so start with **50+ GB free** for a full environment.
The added MOMENT foundation checkpoint is ~1.3855 GB. Native PyTorch and other
scientific dependencies add further gigabytes; total installed size depends on
platform, version, model caching and derived results.

## Dataset integrity and actual limits

- Download is user-initiated and directed to the official PhysioNet link with HTTPS.
- Downloader handles resume where the upstream server supports HTTP Range.
- Extractor rejects unsafe paths, symbolic links, duplicate case-insensitive paths,
  oversized ZIP contents, and encrypted entries; ZIP CRC is checked during extraction.
- The archive is SHA-256 hashed and a local receipt stores its source, version,
  download date, declared license, byte size and checksum.
- The source's SHA256SUMS are not automatically compared to every extracted file
  in v3. A locally recorded SHA-256 is **not** a publisher-verified signature.
- For ZIP sources such as Sleep-EDF where data are already in EDF format,
  indexing WFDB headers returns zero; use the EDF importer instead.
- A dataset can contain imperfect annotations or data-quality issues. The
  downloader does not claim any medical validation or complete annotation harmonization.
- The dataset manager does not train a diagnosis model from source labels automatically.
  Researcher-created human quality annotations and strict grouped splits are required
  for the existing 1D CNN training task.

**Do not upload patient-identifying recordings to third-party services.** Keep data
in access-controlled local folders and consult your institution's ethics and data
stewardship policies. The base software is not a hardened clinical records system.
