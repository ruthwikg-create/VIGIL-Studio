# VIGIL Studio 4.4 – Approved signal brand integration

The original user-supplied artwork is kept unchanged in `vigil_studio/assets/vigil_full_logo_original.png`.
The waveform/frame symbol was cropped strictly from that asset and resized to a square PNG and multi-resolution ICO for the native desktop icon. The rest of the wordmark is presented as application typography in the dark sidebar to maintain contrast at small sizes.

### Places updated

- Sidebar visual mark: now waveform symbol, beside VIGIL STUDIO / INSTRUMENT WORKBENCH labels.
- Windows title-bar icon and app-switcher icon: matching waveform symbol.
- Window title: `VIGIL Studio 4.4 | Instrument Workbench | Developed By Ruthwik Goparaju`.
- Desktop status footer: `Developed By Ruthwik Goparaju`.
- PyInstaller build scripts: include asset files and set `--icon` to the new `.ico` file.

### Important distinctions

This is a branding release; it does **not** make biomedical analysis clinical-grade. Research-only restrictions remain in the application. Windows title bar dimensions and text rendering are OS-controlled. The Windows `.exe` has not been built or tested in this Linux environment.
