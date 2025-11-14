import requests
from requests.adapters import HTTPAdapter, Retry
from typing import Any, Dict, List, Optional


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # --- Helpers ---
    def _get(self, path: str, timeout: Optional[float] = None) -> Any:
        url = f"{self.base_url}{path}"
        t = timeout if timeout is not None else self.timeout
        r = self.session.get(url, timeout=t)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: Optional[dict] = None, timeout: Optional[float] = None) -> Any:
        url = f"{self.base_url}{path}"
        t = timeout if timeout is not None else self.timeout
        r = self.session.post(url, json=json, timeout=t)
        r.raise_for_status()
        return r.json()

    # --- Endpoints ---
    def connect(self) -> Dict[str, Any]:
        return self._get("/connect")

    def disconnect(self) -> Dict[str, Any]:
        return self._get("/disconnect")

    def get_dtc(self) -> List[List[str]]:
        # Returns list of [code, description]
        return self._get("/dtc")

    def get_freeze(self) -> Dict[str, str]:
        return self._get("/freeze")

    def clear_codes(self) -> Dict[str, Any]:
        return self._get("/clear")

    def start_live(self) -> Dict[str, Any]:
        return self._get("/live/start")

    def stop_live(self) -> Dict[str, Any]:
        return self._get("/live/stop")

    def get_live_data(self) -> Dict[str, str]:
        return self._get("/live/data")

    def explain_code(self, code: str) -> Dict[str, Any]:
        # Explain can be slower (cloud call). Allow longer timeout here to match backend.
        return self._get(f"/dtc/explain/{code}", timeout=70)
