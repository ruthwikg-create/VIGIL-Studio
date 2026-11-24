# VIGIL Studio 4.3 — Workbench layout and navigation corrections

## Corrected from the reported Windows screenshot

1. **Sidebar numbers are now sequential.** The list runs 01–05 Workspace, 06–08 Models, 09–12 Data & Evidence, **13 ECG Validation**, **14 Settings**. The research module is no longer inserted between 05 and 06.
2. **Navigation is wider and adjusts to text size.** The rail reserves enough space for the longest navigation item, with a minimum width of 252 logical pixels. A scrollbar appears only when the navigation needs it, and clicking a page scrolls its entry into view.
3. **Workspace and header are separated by explicit padding.** The header and content panels begin to the right of the navigation rail and are checked for non-overlap.
4. **Compact workbench:** If the remaining application width becomes too small for useful ECG plots, the extra right inspector is hidden. Larger windows retain the three resizable panels. Use Signal Lab for detailed per-channel metadata when the inspector is hidden.
5. **Library actions are always reachable.** The OPEN CASE and IMPORT FILE buttons reserve space at the bottom of the source pane instead of being pushed below the window by the list.
6. **Explanatory text wraps.** Overview, ECG Validation and Settings descriptions respond to the panel width instead of drawing beyond the usable workspace.
7. **Toolbar stays usable.** On narrow windows, the duplicated OFFLINE and record-name badges are hidden first, leaving IMPORT, CASE LIBRARY, SYNTHETIC TEST and SETTINGS visible; record state remains available in the page context and record metadata.
8. **No data changes:** Signal processing, waveform files, independent ECG benchmark and local case/annotation storage schemas remain unchanged.

## Test matrix

The layout was rendered under a virtual desktop at **1650×900** with 11/15 pt navigation, **1280×800** with 9 pt navigation, and **1120×720** with 18 pt navigation. These tests check sidebar/container non-overlap, header position, the right panel's compact adaptation, and that Settings can be scrolled into view. All 14 sections were opened, and the sidebar font preference survived a restart. Screenshots are in `examples/LAYOUT_*_V4_3.png`.

Run the scientific regression suite with `RUN_SELF_TEST_WINDOWS.bat`, and verify the release integrity with `python scripts/verify_release.py`. The layout was tested under Linux/Tk using a virtual X display; Windows-specific DPI and taskbar conditions still need local confirmation.

## Installation

Extract this version into **a different folder** from v4.2; run `START_WINDOWS.bat`. Your case database is retained at its prior user-workspace path (unless you configured a custom location). Sidebar font preferences remain in `%APPDATA%\VIGILStudio\settings.json` on Windows. No clinical or diagnostic validity is implied by these interface fixes.
