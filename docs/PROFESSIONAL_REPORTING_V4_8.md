# VIGIL Studio v4.8 - Professional Research Reporting

## Design purpose

The reporting environment is a professional, reviewer-friendly engineering artifact generator, not a medical diagnosis product. It visually matches the VIGIL instrument workbench: charcoal headings, copper separators and signal-specific waveform colors. The selected pulse logo and developer credit remain unchanged.

## Desktop workflow

Open a research recording, then go to **10 Reports & Exports**. The Evidence Studio offers:

- **Full research PDF dossier:** paginated A4 report with recording source, SHA-256, descriptive quality indices, waveform plots, window trends, reviewer notes, limitations and controlled release statement.
- **Complete evidence package:** ZIP with professionally styled PDF, offline HTML index, JSON case report, CSV of window measurements, data dictionary, checksums and a README.
- **Verification:** choose the evidence ZIP and verify all included files against the manifest without extraction. This detects corruption relative to the included manifest, but does NOT independently authenticate the package or certify medical correctness.
- **Machine-readable exports:** JSON, CSV of time-window features and separately confirmed waveform segments. Scientific numeric columns are preserved for MATLAB/Python workflows.

The page is scrollable and switches from two columns to one on narrow screens or with enlarged sidebar text.

## Separate research reports for clinical engineering review

- `RUN_HOSPITAL_READINESS_CHECK_WINDOWS.bat` produces **READINESS_ASSESSMENT.pdf**, `READINESS.json` and `READINESS.md`. Engineering integrity and clinical authorization remain separate outcomes.
- `RUN_MITBIH_VERIFICATION_WINDOWS.bat` produces **BENCHMARK_RESEARCH_REPORT.pdf**, `REPORT.md`, `results.json`, `per_record_metrics.csv`, timing records and a locked protocol. Its data come from the user's actual WFDB files on the user's machine; no benchmark results are bundled or invented.
- `GENERATE_REFERENCE_REPORT_WINDOWS.bat` creates a styled expert-annotation inventory from a locally exported `100_reference_annotations.csv`. **Reference counts are not AI predictions.**

## Clinical interpretation limits

A professional-looking document does not convert research-only software into an approved medical device. A completed benchmark can be a valid engineering result while clinical deployment remains unapproved. The user and hospital must establish the intended use, clinical performance targets, quality management, security and privacy processes, usability and independent medical/regulatory reviews.

The sample signal dossier and engineering-readiness report shipped in `examples` contain **synthetic engineering data only**. The example reference-label inventory is generated from the user-provided **published MIT-BIH Record 100** annotations and contains no model predictions.

## Security and reproducibility

The evidence ZIP does not include raw arrays but **may include reviewer notes and metadata**. De-identification, permission and authorized recipient review are required before sharing. Its SHA-256 manifest is not a digital signature. Current VIGIL research workspaces are not fully encrypted at rest and lack authenticated institutional accounts. Do not load identifiable hospital patient records into this software.
