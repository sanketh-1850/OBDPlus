# Launcher and packaging

This `launcher/` folder contains a small application that starts the FastAPI
backend and then runs the PyQt UI in the same process. It is intended to be
frozen with PyInstaller as an `--onedir --windowed` bundle so end users can
double-click the produced `EXE` and run the whole app without installing
Python or dependencies.

Files
- `run_app.py` — launcher script. Starts uvicorn programmatically in a
  background thread, waits for `/openapi.json` readiness, then imports and
  runs `ui.app` (which should start the QApplication main loop). Logs are
  written to `launcher/logs/`.
- `run_app.bat` — convenience wrapper for testing from source on Windows.

Build (PyInstaller)
1. Create and activate your Windows venv with all dependencies installed.
2. From project root run:

```powershell
pyinstaller --name OBDPlusLauncher --onedir --windowed \
  launcher/run_app.py \
  --add-data "ui;ui" \
  --add-data "assets;assets" \
  --hidden-import "uvicorn" --hidden-import "uvicorn.subprocess"
```

Notes
- On Windows `--add-data` uses `;` as the separator (source;dest).
- If PyInstaller reports additional missing imports, add them with
  `--hidden-import`.
- Test the produced `dist/OBDPlusLauncher/OBDPlusLauncher.exe` on a clean
  Windows VM. If the EXE fails with a missing DLL, the Microsoft Visual
  C++ Redistributable may be required on the target machine.

Troubleshooting
- If the app fails to start, run the EXE from `cmd.exe` to observe logs, or
  inspect the log file created in `launcher/logs/` for a timestamped run.
- Ensure any OBD adapter is paired/driver-installed and visible under
  Device Manager → Ports (COM & LPT).
