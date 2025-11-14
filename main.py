from fastapi import FastAPI, HTTPException
from obd_manager import OBDManager
import cloud_client as cloud
from obd_functions import (
    get_dtc_codes, get_freeze_frame, clear_dtc,
    start_live_polling, stop_live_polling, get_latest_live_data
)

app = FastAPI()
obd_mgr = OBDManager()

@app.get("/connect")
def connect_obd():
    # Guard against duplicate connection attempts
    existing = obd_mgr.get_conn()
    if existing and existing.is_connected():
        return {"status": "already_connected"}
    try:
        if obd_mgr.connect(test=True):  # test mode per current setup
            return {"status": "connected"}
        return {"status": "failed"}
    except Exception as e:
        print(f"/connect error: {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/disconnect")
def disconnect():
    """Stop live polling and close OBD connection safely."""
    try:
        stop_live_polling()
    except Exception:
        pass
    conn_obj = obd_mgr.get_conn()
    if conn_obj and conn_obj.is_connected():
        try:
            obd_mgr.disconnect()
            return {"status": "disconnected"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error disconnecting: {e}")
    return {"status": "not_connected"}


@app.get("/dtc")
def dtc_codes():
    return get_dtc_codes(obd_mgr.get_conn())

@app.get("/freeze")
def freeze_frame():
    return get_freeze_frame(obd_mgr.get_conn())

@app.get("/clear")
def clear_codes():
    return {"result": clear_dtc(obd_mgr.get_conn())}

@app.get("/live/start")
def start_live():
    start_live_polling(obd_mgr.get_conn())
    return {"status": "started"}

@app.get("/live/stop")
def stop_live():
    stop_live_polling()
    return {"status": "stopped"}

@app.get("/live/data")
def live_data():
    return get_latest_live_data()

@app.get("/dtc/explain/{code}")
def explain_code(code: str):
    """
    Gets freeze-frame from OBD, then sends {code, freeze_frame}
    to Render backend for Gemini explanation.
    """
    conn = obd_mgr.get_conn()
    if not conn:
        raise HTTPException(status_code=400, detail="Not connected")

    freeze_frame_data = get_freeze_frame(conn)

    # Call cloud explain with a conservative timeout and robust error handling.
    try:
        explanation = cloud.get_dtc_explanation_from_cloud(code, freeze_frame_data, timeout=70)
    except Exception as e:
        # Defensive: cloud_client should return dicts, but guard anyhow
        explanation = {"error": f"Explain service failed: {e}"}

    # If the cloud returned an error dict, propagate it to the UI (so user sees a friendly message)
    if isinstance(explanation, dict) and explanation.get("error"):
        return {
            "code": code,
            "freeze_frame": freeze_frame_data,
            "explanation": explanation
        }

    # Normal successful case
    return {
        "code": code,
        "freeze_frame": freeze_frame_data,
        "explanation": explanation
    }