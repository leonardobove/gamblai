"""
Authenticated HTTP client for the Kalshi API v2.

Demo base URL:  https://demo-api.kalshi.co/trade-api/v2
Prod base URL:  https://trading-api.kalshi.com/trade-api/v2
"""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from kalshi.auth import make_headers

log = structlog.get_logger()

_API_PREFIX = "/trade-api/v2"


class KalshiClient:
    def __init__(self, base_url: str, key_id: str, private_key_path: str, timeout: float = 15.0):
        self._base_url = base_url.rstrip("/")
        self._key_id = key_id
        self._private_key_path = private_key_path
        self._timeout = timeout

    def _headers(self, method: str, path: str) -> dict[str, str]:
        # path for signing must be the API path only (no query string)
        return make_headers(method, path, self._key_id, self._private_key_path)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def get(self, endpoint: str, params: dict | None = None) -> dict:
        path = f"{_API_PREFIX}{endpoint}"
        headers = self._headers("GET", path)
        url = f"{self._base_url}{path}"
        resp = httpx.get(url, headers=headers, params=params, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def post(self, endpoint: str, body: dict) -> dict:
        path = f"{_API_PREFIX}{endpoint}"
        headers = self._headers("POST", path)
        url = f"{self._base_url}{path}"
        resp = httpx.post(url, headers=headers, json=body, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def delete(self, endpoint: str) -> dict:
        path = f"{_API_PREFIX}{endpoint}"
        headers = self._headers("DELETE", path)
        url = f"{self._base_url}{path}"
        resp = httpx.delete(url, headers=headers, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    def get_balance(self) -> float:
        """Return available balance in dollars."""
        data = self.get("/portfolio/balance")
        return data["balance"] / 100.0  # cents → dollars

    def ping(self) -> bool:
        """Check connectivity and auth."""
        try:
            self.get_balance()
            return True
        except Exception as e:
            log.warning("kalshi_ping_failed", error=str(e))
            return False
