# Running the new verification tests on Windows

This release contains your familiar VIGIL Studio v4.4 interface and logo. The **new feature is a separate, controlled retrospective benchmark**, not a medical-grade diagnostic mode.

1. Extract the ZIP to a new directory. **Do not copy it over a running older installation.**
2. Run `START_WINDOWS.bat` once; this creates the isolated `.venv` and opens the familiar desktop.
3. Close VIGIL Studio before running the benchmark.
4. Double-click `RUN_MITBIH_VERIFICATION_WINDOWS.bat`.
5. When prompted for the MIT-BIH directory, enter `D:\Biomedical_Datasets\MITBIH` (or leave blank if that is where you saved the original dataset).
6. Choose `1` for Record 100. This is only an engineering smoke test.
7. Open the output directory displayed in the terminal, normally under your Documents folder, and inspect `REPORT.md` and `per_record_metrics.csv`.
8. If Record 100 runs correctly, run the batch file again and choose `2` to benchmark all **48 published MIT-BIH records**. A missing file or processing error is reported, not silently skipped.

If you prefer to run from Command Prompt with an explicit output folder:

```cmd
cd /d "D:\path\to\VIGIL_Studio_v4_4_Clinical_Readiness_Gate1"
.venv\Scripts\python.exe scripts\clinical_readiness_benchmark.py --dataset "D:\Biomedical_Datasets\MITBIH" --record 100 --out "D:\VIGIL_Results_Record100_FirstRun"
.venv\Scripts\python.exe scripts\clinical_readiness_benchmark.py --dataset "D:\Biomedical_Datasets\MITBIH" --out "D:\VIGIL_Results_All48_FirstRun"
```

**Important:** Pick an output folder name that does not exist. A prior report is intentionally never overwritten. Do not enter output paths within patient clinical-data folders.

## Files produced

- `locked_protocol.json`: fixed protocol ID, 150 ms comparison tolerance, source hashes, and software scope.
- `per_record_metrics.csv`: per-record performance including missed and extra detections.
- `results.json`: detailed per-record source/provenance hashes and errors.
- `record_events/`: independently matched event listings and detailed JSON for each completed record.
- `REPORT.md`: human-readable summary and worst-performing records.

## What counts as success?

- **Execution success:** Requested original recordings were present, readable, correctly processed, and all results exported.
- **Clinical performance acceptance:** **Not determined**. A separate intended use, safety-risk analysis, clinical team, independent external validation, and applicable regulatory oversight are still necessary.

**This benchmark cannot diagnose arrhythmia. It cannot establish medical-grade status or clinical-trial success. Do not put it in a clinical care pathway.**
