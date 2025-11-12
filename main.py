from fastapi import FastAPI
from obd_manager import OBDManager
from obd_functions import (
    get_dtc_codes, get_freeze_frame, clear_dtc,
    start_live_polling, stop_live_polling, get_latest_live_data
)

app = FastAPI()
obd_mgr = OBDManager()

@app.get("/connect")
def connect_obd():
    if obd_mgr.connect():
        return {"status": "connected", "port": obd_mgr.get_conn().port_name()}
    return {"status": "failed"}

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