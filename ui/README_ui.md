# OBD++ Desktop UI (PyQt6)

A lightweight desktop frontend for the existing FastAPI backend in this repo. It connects to the running server at `http://127.0.0.1:8000` and provides pages for:

- Connect (Landing)
- Read Codes (with "Explain with AI")
- Live Sensor Data
- Freeze Frame Data
- Clear Codes

## Structure
- `ui/app.py` – App entry point
- `ui/api_client.py` – HTTP client for backend endpoints
- `ui/windows/main_window.py` – Main window, side menu, page routing
- `ui/pages/` – Individual pages
  - `landing_page.py`, `dtc_page.py`, `live_page.py`, `freeze_page.py`, `clear_page.py`
- `ui/utils/workers.py` – `QRunnable` wrapper for background calls
- `ui/resources/style.qss` – Styling (dark theme)

## Prereqs
- Backend running (FastAPI): in repo root run:

```powershell
# from repo root
uvicorn main:app --reload
```

- For simulated OBD per `Steps_to_run.txt`: VSPE COM8<->COM9, `obdsim` on COM8, app uses COM9 by default.

## Install UI deps
```powershell
pip install -r ui/requirements.txt
```

## Run the UI
```powershell
python ui/app.py
```

## Notes
- Closing the app stops live polling and calls `/disconnect`.
- Live page starts polling when visible and stops when you navigate away.
- "Explain with AI" renders HTML returned by `/dtc/explain/{code}`. If the backend returns a JSON wrapper `{ explanation: "<html>..." }`, the UI extracts and displays it.
