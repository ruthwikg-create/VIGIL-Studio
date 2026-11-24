# VIGIL Studio v4.1 — ECG Reference Validation

This is an independent **beat-location comparison**, not an arrhythmia classifier or a medical diagnostic assessment.

## Windows walk-through for MIT-BIH Record 100

1. Keep `100.hea`, `100.dat`, and `100.atr` together in the same directory, e.g. `D:\Biomedical_Datasets\MITBIH`.
2. Extract the **v4.1** release into a new folder. Do not overwrite or delete your working v4 folder.
3. Run `START_WINDOWS.bat` inside the new folder. It prioritizes installed Python 3.12. Libraries are installed into a project-specific `.venv`.
4. On the sidebar click **13 ECG Validation**. Then **IMPORT ORIGINAL .HEA + .DAT + .ATR**; select `D:\Biomedical_Datasets\MITBIH\100.hea`.
5. Wait for import and signal analysis to complete. This version requests the entire WFDB record, subject to its 8,000,000-sample-per-channel safety cap.
6. Return to **13 ECG Validation**. Select `MLII`, `START 600`, `SPAN 10`, then **PLOT MARKERS**. Dashed teal lines and `N`, `A`, `V` letters are the **original published `.atr` references**, not predictions.
7. Select matching tolerance **0.15 seconds**, then choose **RUN INDEPENDENT PEAK TEST**. The orange triangles are detector predictions generated from the signal **without using any `.atr` labels**.
8. Read the matching counts and export both JSON and event-level CSV if needed. The exports include source identity, thresholds and unmatched events.
9. Optional independent command-line replication (run from the extracted v4.1 folder):

   ```cmd
   .venv\Scripts\python.exe scripts\benchmark_mitbih.py "D:\Biomedical_Datasets\MITBIH\100.hea" --channel MLII --out research_results_100
   ```

## What is compared

- Ground truth: only known WFDB heartbeat **point annotations** from the `.atr` file. Non-beat event markers such as `+` are excluded.
- Prediction: existing VIGIL heuristic peak finder on ECG signal values. This is **not a trained neural classifier**.
- Matching: ordered one-to-one comparison with fixed ±0.15 s tolerance (user-adjustable for sensitivity analysis).
- Reported: TP, FP, FN, reference beat counts by symbol, sensitivity/recall, positive predictive value, F1, median and 95th-percentile absolute timing error.
- Quality indices are **not** used as diagnostic or arrhythmia labels. Manual quality annotations stay separate from `.atr` ground truth.

## Scientific limitations

- R-peak location detection is not **arrhythmia classification**. The model does **not** identify atrial premature or ventricular premature beat types from the ECG; it only attempts to localize peaks.
- Reference symbols such as `N`, `A`, and `V` shown on plots came from PhysioNet and must not be presented as the software's predicted classes.
- A single 30-minute recording, even with good agreement, does not demonstrate clinical validity, transportability or medical-grade performance.
- Peak detector remains a heuristic; it can misidentify tall T waves, movement artifacts, ectopy, inverted QRS complexes and noisy data.
- The test suite and screenshot in this release used artificial ECG examples. The original MIT-BIH `.dat` file was not present in the build environment, so the completed full-record benchmark was **not** measured here.
- Patient data must be appropriately de-identified and used under the applicable permissions. This desktop application is an offline single-user research tool, not a clinical record system.

## Source files

- `vigil_studio/core/ecg_validation.py` — auditable reference parsing, matching and research result export.
- `vigil_studio/core/importers.py` — full-length local WFDB import and local waveform/annotation SHA-256.
- `vigil_studio/ui/app.py` — integrated ECG Validation screen.
- `scripts/benchmark_mitbih.py` — headless repeatable benchmark.
- `tests/test_ecg_validation_v41.py` — synthetic engineering regression tests.

**Full MIT-BIH dataset:** https://physionet.org/content/mitdb/1.0.0/
