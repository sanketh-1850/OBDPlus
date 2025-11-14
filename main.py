from fastapi import FastAPI, HTTPException
import threading
import time
import requests
from datetime import datetime

from obd_manager import OBDManager
import cloud_client as cloud
from obd_functions import (
    get_dtc_codes, get_freeze_frame, clear_dtc,
    start_live_polling, stop_live_polling, get_latest_live_data
)

app = FastAPI()
obd_mgr = OBDManager()


# --------------------------------------------------------
# 1. Lightweight ping endpoint (Render-friendly)
# --------------------------------------------------------
@app.get("/ping")
def ping():
    return {"ok": True}

# --------------------------------------------------------
# 2. Keep-align function (self-ping)
# --------------------------------------------------------
RENDER_URL = "https://obdpluscloud.onrender.com/ping"  # your Render URL

def keep_alive():
    while True:
        try:
            res = requests.get(RENDER_URL, timeout=10)
            print("PING:", res.status_code, datetime.now())
        except Exception as e:
            print("Ping error:", e)
        time.sleep(600)  # every 1 minute

# --------------------------------------------------------
# 3. Start keep-alive background thread on startup
# --------------------------------------------------------
@app.on_event("startup")
def start_keep_alive_thread():
    thread = threading.Thread(target=keep_alive, daemon=True)
    thread.start()
    print("🔥 Keep-alive thread started")



@app.get("/connect")
def connect_obd():
    if obd_mgr.connect():
        return {"status": "connected", "port": obd_mgr.get_conn().port_name()}
    return {"status": "failed"}

@app.get("/disconnect")
def disconnect():
    """
    Safely disconnect from the OBD-II adapter.
    Stops live polling and closes the OBD connection.
    """
    # Stop live data polling if running
    try:
        from obd_functions import stop_live_polling
        stop_live_polling()
    except:
        pass

    # Close OBD-II connection
    if obd_mgr.conn:
        try:
            obd_mgr.conn.close()
            obd_mgr.conn = None
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
    explanation = cloud.get_dtc_explanation_from_cloud(code, freeze_frame_data)

    return {
        "code": code,
        "freeze_frame": freeze_frame_data,
        "explanation": explanation
    }