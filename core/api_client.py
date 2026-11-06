"""
API-client voor de Prosperia V2 backend.

De bot praat NIET direct met MariaDB: de database luistert alleen op een
Unix-socket op de shared hosting (localhost:/tmp/mysql5.sock). De Raspberry Pi
kan daar dus niet bij. Alle data gaat via de PHP API.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Fout bij het communiceren met de Prosperia API."""

    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class ProsperiaApiClient:
    """Dunne client rond de Prosperia PHP API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        timeout: float = 15.0,
        max_retries: int = 3,
        token_refresh_margin: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.token_refresh_margin = token_refresh_margin

        self._token: str | None = None
        self._token_expires_at: float = 0.0

        self._session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def login(self) -> None:
        """Vraag een nieuw token aan bij de API."""
        url = f"{self.base_url}/index.php"
        payload = {"action": "login", "username": self.username, "password": self.password}
        logger.info("Inloggen bij Prosperia API als %s", self.username)

        try:
            resp = self._session.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ApiError(f"Login mislukt: {exc}") from exc

        if resp.status_code != 200:
            raise ApiError("Login geweigerd", resp.status_code, self._safe_json(resp))

        data = self._safe_json(resp) or {}
        token = data.get("token") or data.get("access_token")
        if not token:
            raise ApiError("Login response bevat geen token", resp.status_code, data)

        self._token = token
        expires_in = int(data.get("expires_in", 3600))
        self._token_expires_at = time.time() + max(expires_in - self.token_refresh_margin, 30)
        logger.info(
            "Login OK, token geldig tot %s",
            time.strftime("%H:%M:%S", time.localtime(self._token_expires_at)),
        )

    def _ensure_token(self) -> None:
        if self._token is None or time.time() >= self._token_expires_at:
            self.login()

    def _auth_headers(self) -> dict[str, str]:
        self._ensure_token()
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, payload: dict[str, Any] | None = None) -> Any:
        return self._request("POST", endpoint, json_body=payload)

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in (1, 2):
            headers = self._auth_headers()
            try:
                resp = self._session.request(
                    method, url, headers=headers, params=params, json=json_body, timeout=self.timeout
                )
            except requests.RequestException as exc:
                raise ApiError(f"{method} {endpoint} mislukt: {exc}") from exc

            if resp.status_code == 401 and attempt == 1:
                logger.warning("Token verlopen, opnieuw inloggen")
                self._token = None
                continue

            if resp.status_code >= 400:
                raise ApiError(
                    f"{method} {endpoint} -> HTTP {resp.status_code}",
                    resp.status_code,
                    self._safe_json(resp),
                )

            return self._safe_json(resp)

        raise ApiError(f"{method} {endpoint} definitief mislukt na token-refresh")

    @staticmethod
    def _safe_json(resp: requests.Response) -> Any:
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}
