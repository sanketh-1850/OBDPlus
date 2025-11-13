import requests

RENDER_API_URL = "https://obdpluscloud.onrender.com/explain"  # Replace with your real Render URL

def get_dtc_explanation_from_cloud(code, freeze_frame):
    """
    Sends DTC + freeze frame data to Render backend for explanation.
    Returns a JSON dict with 'explanation' or 'error'.
    """
    payload = {"code": code, "freeze_frame": freeze_frame}

    try:
        res = requests.post(RENDER_API_URL, json=payload)
        if res.status_code == 200:
            return res.json()
        else:
            return {"error": f"Render API error {res.status_code}: {res.text}"}
    except Exception as e:
        return {"error": str(e)}