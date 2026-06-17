"""Thin async HTTP client for the Agent Mail backend REST API."""

from __future__ import annotations

import uuid
from typing import Any, Optional

import httpx


class AgentMailError(Exception):
    """Raised when the backend returns an error response."""


class AgentMailClient:
    """Wraps the Agent Mail REST API.

    The instance *secret* is a UUID that doubles as the API credential. If the
    server has an admin token configured, pass it as ``admin_token`` and it is
    sent as ``X-Admin-Token`` on every request.
    """

    def __init__(
        self,
        base_url: str,
        admin_token: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"Content-Type": "application/json"}
        if admin_token:
            self._headers["X-Admin-Token"] = admin_token
        self._timeout = timeout

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base}/api{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as http:
            resp = await http.request(method, url, headers=self._headers, **kwargs)
        if resp.status_code >= 400:
            detail = resp.text
            try:
                body = resp.json()
                detail = body.get("error") or body.get("detail") or detail
            except Exception:
                pass
            raise AgentMailError(f"{method} {path} -> {resp.status_code}: {detail}")
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # ── Instances ────────────────────────────────────────────────────────────
    async def get_or_create_instance(self, secret: str) -> dict:
        """GET auto-creates the instance if it does not exist."""
        return await self._request("GET", f"/instances/{secret}")

    async def update_instance(self, secret: str, **fields: Any) -> dict:
        return await self._request("PUT", f"/instances/{secret}", json=fields)

    async def delete_instance(self, secret: str) -> Any:
        return await self._request("DELETE", f"/instances/{secret}")

    # ── Keys ─────────────────────────────────────────────────────────────────
    async def list_keys(self, secret: str) -> list[dict]:
        return await self._request("GET", f"/instances/{secret}/keys")

    async def add_key(self, secret: str, key: str) -> dict:
        return await self._request("POST", f"/instances/{secret}/keys", json={"key": key})

    async def remove_key(self, secret: str, key: str) -> Any:
        return await self._request("DELETE", f"/instances/{secret}/keys/{key}")

    # ── Custom domains ───────────────────────────────────────────────────────
    async def list_domains(self, secret: str) -> list[dict]:
        return await self._request("GET", f"/instances/{secret}/domains")

    async def add_domain(self, secret: str, domain: str) -> dict:
        return await self._request("POST", f"/instances/{secret}/domains", json={"domain": domain})

    async def verify_domain(self, secret: str, domain: str) -> dict:
        return await self._request("POST", f"/instances/{secret}/domains/{domain}/verify")

    async def remove_domain(self, secret: str, domain: str) -> Any:
        return await self._request("DELETE", f"/instances/{secret}/domains/{domain}")

    # ── Emails ───────────────────────────────────────────────────────────────
    async def list_emails(
        self,
        secret: str,
        skip: int = 0,
        limit: int = 50,
        from_email: Optional[str] = None,
        nickname: Optional[str] = None,
        extracted_key: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> dict:
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        if from_email:
            params["from_email"] = from_email
        if nickname:
            params["nickname"] = nickname
        if extracted_key:
            params["extracted_key"] = extracted_key
        if subject:
            params["subject"] = subject
        return await self._request("GET", f"/instances/{secret}/emails", params=params)

    async def get_email(self, secret: str, email_id: str) -> dict:
        return await self._request("GET", f"/instances/{secret}/emails/{email_id}")


def new_secret() -> str:
    """Generate a fresh instance secret (UUIDv4)."""
    return str(uuid.uuid4())
