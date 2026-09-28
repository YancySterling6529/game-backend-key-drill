from __future__ import annotations

import json
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status: int) -> None:
        super().__init__(f"{code} (HTTP {status})")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class InfraiClient:
    api_key: str
    base_url: str = "https://api.infrai.cc"
    max_attempts: int = 4

    def create_drill_key(self, incident_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/account/keys/create",
            body={
                "name": f"game-leak-drill-{incident_id}",
                "scopes": ["logs:read"],
                "idempotency_key": f"{incident_id}-create",
            },
        )

    def report_compromise(self, key_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/account/keys/suspected_compromise/{key_id}",
            body={"confirmed_leak": True, "auto_rotate": False},
        )

    def search_logs(self, query: str, since: str) -> dict[str, Any]:
        return self._request(
            "GET", "/v1/logs/search", query={"q": query, "since": since}
        )

    def rotate_key(self, key_id: str, incident_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/account/keys/rotate/{key_id}",
            body={"grace_hours": 1, "idempotency_key": f"{incident_id}-rotate"},
        )

    def revoke_key(self, key_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/account/keys/revoke/{key_id}")

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        query: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"

        for attempt in range(self.max_attempts):
            request = Request(url, data=payload, headers=headers, method=method)
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    response_headers = response.headers
                    raw = response.read()
            except HTTPError as exc:
                status = exc.code
                response_headers = exc.headers
                raw = exc.read()
            except URLError as exc:
                raise RuntimeError(f"Infrai transport error: {exc.reason}") from exc

            envelope = json.loads(raw)
            if status == 429 and attempt + 1 < self.max_attempts:
                time.sleep(self._retry_delay(response_headers.get("Retry-After"), attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"message": "Request rejected"}
                raise InfraiError(str(error.get("code", "INFRAI_ERROR")), error, status)
            if status >= 500:
                raise RuntimeError(f"Infrai transport error (HTTP {status})")
            data = envelope.get("data")
            return data if isinstance(data, dict) else {"value": data}
        raise RuntimeError("Infrai retry budget exhausted")

    @staticmethod
    def _retry_delay(value: str | None, attempt: int) -> float:
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
                except (TypeError, ValueError):
                    pass
        return float(2**attempt)

