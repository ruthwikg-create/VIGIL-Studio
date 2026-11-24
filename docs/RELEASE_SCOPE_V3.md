# VIGIL Studio v3 release contract

Release type: **runnable research source application + reproducible large data/model setup scripts**.

## Tested

- Native Tkinter application startup and navigation on Linux/Xvfb, including
  `Research Environment` and original analysis pages.
- Data catalog, path-safe ZIP extraction, synthetic offline archive install,
  archive checksum receipt, metadata indexing, disk inventory, seed-controlled
  robustness report and software model training with generated test signals.
- CPU PyTorch 1D CNN training on synthetic test cohorts, output integrity and
  test/validation grouping via included tests.
- Source ZIP can be independently extracted and tested.

## Not tested / not included

- A Windows `.exe`, MSI installer or Windows runtime execution. Windows scripts
  are provided; build must run on Windows with its Python toolchain.
- Actual large public dataset downloads/extraction at 29 GB in this restricted
  build environment; network access to PhysioNet/Hugging Face is unavailable.
- MOMENT inference after real 1.39 GB checkpoint acquisition, including GPU.
- Diagnostics, alarm suppression, autonomous clinical decisions or FDA/CDSCO clearance.
- Hospital FHIR/HL7 devices, PACS, authenticated PHI/PII store, multi-user security.
- Independent clinical cohort model evaluation, ethics-approved prospective study,
  peer-reviewed publication or successful clinical trial.

## Operational safeguards

- No network activity is triggered by simply opening the desktop application.
- No hidden unbounded background tasks, live patient monitoring or clinical alarms.
- A user must explicitly accept the upstream terms and request the downloads.
- Incomplete downloads are `.zip.partial`, never falsely marked "installed".
- Installed source datasets are never inserted into the project source ZIP.
- Large research data should reside on a user-chosen drive with sufficient free
  space and institutional authorization, NOT in a protected system directory.
