# OBD++

OBD++ is a desktop OBD-II diagnostic assistant that couples an attractive PyQt6 frontend with a FastAPI backend. It reads live sensor data and diagnostic trouble codes (DTCs) from a vehicle's OBD-II port and uses integrated AI explanation to give clear, human-friendly descriptions, likely causes, and suggested fixes for fault codes.

Every car sold since 1996 exposes standardized OBD-II PIDs and DTCs. Most tools only display a code and short description — OBD++ goes further by combining the code description, common fixes, and freeze-frame (snapshot) sensor data with an AI explanation layer so that mechanics and non-technical users get an actionable, easy-to-understand diagnosis.

Key features
- Read live sensor data (RPM, speed, coolant temp, MAF, O2 sensors, timing advance, etc.) and display them in an attractive UI with inline sparklines for each sensor.
- Read active DTCs and view freeze-frame snapshots captured when a code was set.
- "Explain with AI": expanded, plain-language explanation for DTCs that references code meaning, likely causes, and suggested fixes.
- Clear DTCs (when desired) and verify with live data and freeze-frame inspection.
- Background-safe design: long-running operations run in worker threads and the UI remains responsive.

Project layout
- `main.py` — FastAPI backend entry (API endpoints for connect/disconnect, live data, dtcs, explain).
- `obd_functions.py` — OBD access helpers, live polling, and caching.
- `cloud_client.py` — optional cloud explain client used by the backend.
- `ui/` — PyQt6 frontend
	- `ui/app.py` — UI entry point
	- `ui/api_client.py` — HTTP client wrapper used by the UI
	- `ui/windows/` and `ui/pages/` — window and page definitions; `live_page.py` contains the live sensor view
	- `ui/widgets/` — custom widgets (sparklines, etc.)
	- `ui/requirements.txt` — UI dependencies (PyQt6, pyqtgraph, requests)

Prerequisites
- Python 3.10+ (or compatible) and the dependencies listed in `ui/requirements.txt` for the UI and the project-level `requirements.txt` (if present) for backend components.
- Backend server (FastAPI) running locally: from project root run:

```powershell
uvicorn main:app --reload
```

- For simulated OBD testing (optional): virtual serial pair (e.g., VSPE) and `obdsim` connected to one side; configure the app to use the other COM port (see `Steps_to_run.txt`).

Install UI dependencies

```powershell
pip install -r ui/requirements.txt
```

Run the UI

```powershell
python ui/app.py
```

Notes and UX
- The Live page shows sensor rows with three aligned columns: sensor name (left), current value with units (center), and a compact sparkline (right) providing recent history.
- The app uses background workers for blocking API calls and keeps live polling isolated so the UI remains responsive.
- The AI explanation feature returns formatted HTML that the UI presents in a dialog for DTC details.

Contributing and development
- The project is organized to separate UI and backend concerns; UI changes can be developed within the `ui/` folder while backend endpoints live at the project root. If you run the backend and UI locally you can iterate quickly.
