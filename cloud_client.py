import requests
from requests.adapters import HTTPAdapter, Retry

RENDER_API_URL = "https://obdpluscloud.onrender.com/explain"  # Replace with your real Render URL

# Session with light retry policy to avoid long blocking
_session = requests.Session()
_retries = Retry(total=1, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
_session.mount("https://", HTTPAdapter(max_retries=_retries))
_session.mount("http://", HTTPAdapter(max_retries=_retries))


def get_dtc_explanation_from_cloud(code, freeze_frame, timeout: int = 60):
    """
    Sends DTC + freeze frame data to Render backend for explanation.
    Returns a JSON dict with 'explanation' or {'error': <message>}.
    Uses a timeout (default 60s) to allow slower provider responses when needed.
    """
    payload = {"code": code, "freeze_frame": freeze_frame}

    try:
        res = _session.post(RENDER_API_URL, json=payload, timeout=timeout)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Cloud request failed: {e}"}
    except Exception as e:
        return {"error": str(e)}