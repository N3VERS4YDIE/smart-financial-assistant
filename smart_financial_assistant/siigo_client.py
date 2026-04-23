"""HTTP client wrapper for authenticated access to SIIGO financial endpoints."""

from __future__ import annotations

import time
from typing import Any

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Settings


class SiigoClient:
    """Handle SIIGO authentication, retries, and report API requests."""

    def __init__(self, settings: Settings, timeout: int = 60) -> None:
        """Create a resilient SIIGO session with retry policy and token cache."""
        self._settings = settings
        self._timeout = timeout
        self._token: str | None = None
        self._token_expires_at = 0.0

        retry = Retry(
            total=3,
            backoff_factor=0.4,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
        )
        self._session = requests.Session()
        self._session.mount("https://", HTTPAdapter(max_retries=retry))

    def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send an authenticated JSON request to SIIGO and return the parsed payload."""
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Partner-Id": self._settings.siigo_partner_id,
            "Content-Type": "application/json",
        }
        url = f"{self._settings.siigo_base_url.rstrip('/')}/{path.lstrip('/')}"
        response = self._session.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            timeout=self._timeout,
        )
        self._raise_for_status(response)
        return response.json() if response.content else {}

    @staticmethod
    def _raise_for_status(response: Response) -> None:
        """Raise a readable runtime error when SIIGO returns an HTTP failure."""
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body_preview = response.text[:500]
            raise RuntimeError(
                f"SIIGO API error {response.status_code}: {body_preview}"
            ) from exc

    def _get_token(self) -> str:
        """Return a cached bearer token or authenticate again when expired."""
        if self._token and time.time() < self._token_expires_at:
            return self._token

        response = self._session.post(
            f"{self._settings.siigo_base_url.rstrip('/')}/auth",
            json={
                "username": self._settings.siigo_username,
                "access_key": self._settings.siigo_access_key,
            },
            headers={"Content-Type": "application/json"},
            timeout=self._timeout,
        )
        self._raise_for_status(response)
        payload = response.json()

        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Auth response does not include access_token")

        # SIIGO token TTL is not returned reliably; refresh every 45 minutes.
        self._token = token
        self._token_expires_at = time.time() + (45 * 60)
        return token

    def get_accounts_payable(self) -> dict[str, Any]:
        """Fetch accounts payable data from SIIGO."""
        return self._request("GET", "/v1/accounts-payable")

    def get_trial_balance(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Fetch trial balance report data from SIIGO."""
        return self._request("POST", "/v1/test-balance-report", json=payload)

    def get_trial_balance_by_thirdparty(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Fetch third-party trial balance report data from SIIGO."""
        return self._request("POST", "/v1/test-balance-report-by-thirdparty", json=payload)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
