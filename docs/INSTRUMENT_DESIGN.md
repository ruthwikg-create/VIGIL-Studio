# VIGIL Studio v4 — Interface design system

**Design archetype:** desktop scientific instrument / research operator workstation, not a SaaS analytics dashboard.

## Working principles
1. Data has primacy: waveforms take most available space, other controls are compact.
2. Adjacent context: channels left, waveform centre, immutable technical information right.
3. Panels are draggable with native Tk/ttk sash controls.
4. No decorative KPI cards on the default view. Record library and trace preview are useful before a recording is imported.
5. Synthetic data clearly marked as synthetic. No patient monitoring is claimed.
6. Source provenance, human review, uncertainty and non-clinical disclaimers remain visible.

## Identity
- **Base:** mineral charcoal `#202A2B`, instrument parchment `#FAFAF6`, warm gray `#E9EBE5`.
- **Operational emphasis:** copper `#D36843`. Not a risk severity code.
- **Channels:** ECG rust, PPG teal, ABP indigo, RESP ochre, EEG violet, EMG green. Colours supplement text labels, never replace them.
- **Fonts:** system-provided Bahnschrift/IBM Plex Sans/Aptos for controls when available; system Consolas/IBM Plex Mono for metadata. Portable fallback is DejaVu Sans / DejaVu Sans Mono. No third-party font is distributed.
- **Panels:** 1 px borders and instrument-divider lines, not rounded cards, shadows or glossy gradients.

## Navigation
- Workspace 01–05: Acquisition desk, Signal Lab, Quality Explorer, Modality Lab, Annotation Studio.
- Research 06–08: AI Experiments, Deep Learning Lab, Foundation Models.
- Evidence 09–12: Research Environment, Reports & Exports, Audit Trail, Guide & Safety.

## Keyboard
Ctrl+O import; Ctrl+L case library; Ctrl+R/F5 refresh; Ctrl+1..9 switch main panels; Ctrl+Left/Right move viewer window.

## Intended future work
- Native dockable plugin containers and detach-to-window plots; configurable workspace layouts persisted on disk.
- Better accessibility testing including keyboard traversal and high-contrast modes.
- Validated signal-annotation interactions and linked time rulers.

This is an engineering UX release, **not a medical usability validation**.
