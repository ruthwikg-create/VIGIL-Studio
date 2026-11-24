# Sidebar text-size settings — VIGIL Studio v4.2

## What is new

The default sidebar text-size is **11 pt** (up from 9 pt in earlier releases). Researchers can adjust it from **9 pt to 18 pt** without changing scientific waveform amplitude, time scales, algorithm outputs, or annotation contents.

### Using the setting

1. Start the application normally with `START_WINDOWS.bat`.
2. Click **SETTINGS** in the top instrument toolbar, or scroll the left navigation to **14 Settings**.
3. Move the **Text size** slider to your preferred value, e.g., **14 pt** or **16 pt**.
4. Navigation text and sidebar width change immediately. The value is saved automatically and restored after a restart.
5. Click **RESET SIZE** to restore **11 pt**.

When font size is large or the application window is short, scroll the navigation with the mouse wheel or use its vertical scrollbar. The toolbar SETTINGS button remains available at all times.

## Preference location

- **Windows:** `%APPDATA%\VIGILStudio\settings.json`
- **Linux:** `$XDG_CONFIG_HOME/VIGILStudio/settings.json` (or `~/.config/VIGILStudio/settings.json`)

The preference file holds only a display size, not waveform data or patient details. It is independent of the VIGILStudio_Workspace case/annotation database, and therefore applies to future installs of v4.2 as well.

The existing research workspace and stored annotations are **not migrated or modified** by changing the sidebar size. v4.2 uses the same default case workspace as v4.1 (`~/VIGILStudio_Workspace`). If you previously used a custom workspace path, launch v4.2 using the same custom workspace path to see those cases.

## Research and clinical limitations

This is an interface/accessibility change only. It adds **no new diagnostic capability** and does not alter ECG analysis, stored annotations, AI training, clinical validation, or regulatory status. Research-only restrictions continue to apply.
