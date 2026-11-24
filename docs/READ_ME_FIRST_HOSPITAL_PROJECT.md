# Start here — the doctor's VIGIL Studio project

**What this ZIP is:** VIGIL Studio v4.6 offline research workstation and tested hospital-readiness *engineering controls*.

**What it is NOT:** A medical-grade, approved, clinically validated hospital monitoring device or deployable patient-care service.

## What was changed in actual code
- Per-archive SHA-256 added on new saved waveforms. Altered saved files are refused on load; old records remain accessible but flagged as legacy unverified during assessment.
- NPZ preflight rejects unexpected members/oversize metadata and declared decompressed data sizes.
- Additional CSV identity-header checks and channel-collision detection.
- Spreadsheet formula injection mitigation for selected CSV export paths.
- Guide & Safety now offers a local integrity check with an unambiguous **CLINICAL RELEASE: BLOCKED** message.
- Offline `RUN_HOSPITAL_READINESS_CHECK_WINDOWS.bat` produces JSON and Markdown gate evidence; does not modify or export source waveforms.
- Existing fixed-protocol MIT-BIH benchmark and user-selected signal logo are retained.

## Windows workflow (Python 3.12)
1. **Keep your existing v4.4 folder.** Extract this ZIP into a new folder. Back up the VIGIL workspace before opening a new version; the SQLite cases table is migrated by adding a digest column.
2. Launch `START_WINDOWS.bat`, then open `12 Guide & Safety`. Click **RUN LOCAL INTEGRITY CHECK**. Research-only label remains.
3. Run `RUN_SELF_TEST_WINDOWS.bat` and save the output.
4. Run `RUN_HOSPITAL_READINESS_CHECK_WINDOWS.bat` to create a numbered local readiness report folder. A nonzero exit means engineering review is required. **A zero exit never allows clinical care.**
5. Run `RUN_MITBIH_VERIFICATION_WINDOWS.bat`, first Record 100, then all 48 original records on `D:\Biomedical_Datasets\MITBIH`. Do not use the converted CSV to claim complete reference benchmark evidence.
6. Return `REPORT.md`, `per_record_metrics.csv` and `READINESS.md` from the relevant tests to your engineering/clinical team. Share only public dataset results and de-identified material permitted for disclosure.

## Hospital qualification steps outside this archive
Clinical sponsor form; approved intended use; CDSCO classification and licensing advice; hospital governance and data protection; a controlled medical-device QMS; design input/verification/validation files; signed risk management; cybersecurity assessment; independent human factors and clinical studies; deployment and maintenance processes. See `HOSPITAL_READINESS_ENGINEERING_V4_6.md`.

The source includes no default hospital credentials, patient data import authorization, live medical equipment control, alarm suppression, or clinical diagnosis feature.
