"""Security middleware: optional admin-token gating and per-IP rate limiting.

Both are opt-in via config (docs/security.md). When disabled they are no-ops, so the
default dev experience is unchanged.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict

from aiohttp import web

from app.config import settings

# Methods that mutate state. GET/HEAD/OPTIONS are considered read-only.
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths that expose cross-instance data and should be admin-gated regardless of method.
_ADMIN_ONLY_PATHS = ("/api/emails/orphaned",)


def _client_ip(request: web.Request) -> str:
    # Honour X-Forwarded-For when behind a trusted proxy; fall back to peer.
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    peer = request.transport.get_extra_info("peername") if request.transport else None
    return peer[0] if peer else "unknown"


@web.middleware
async def admin_token_middleware(request: web.Request, handler):
    """Require X-Admin-Token on mutating and admin-only endpoints, if a token is set."""
    token = settings.ADMIN_API_TOKEN
    if token:
        is_admin_path = any(request.path.startswith(p) for p in _ADMIN_ONLY_PATHS)
        is_mutating = request.method in _MUTATING_METHODS
        if (is_admin_path or is_mutating) and request.method != "OPTIONS":
            provided = request.headers.get("X-Admin-Token", "")
            if provided != token:
                return web.json_response(
                    {"error": "Forbidden", "detail": "Valid X-Admin-Token required"},
                    status=403,
                )
    return await handler(request)


def rate_limit_middleware_factory():
    """Build a simple in-memory sliding-window rate limiter keyed by client IP."""
    limit = settings.RATE_LIMIT_PER_MINUTE
    window = 60.0
    hits: Dict[str, Deque[float]] = {}

    @web.middleware
    async def rate_limit_middleware(request: web.Request, handler):
        if limit <= 0 or request.method == "OPTIONS":
            return await handler(request)
        now = time.monotonic()
        ip = _client_ip(request)
        bucket = hits.setdefault(ip, deque())
        # Drop timestamps outside the window.
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            retry = int(window - (now - bucket[0])) + 1
            return web.json_response(
                {"error": "Too Many Requests", "detail": f"Retry in {retry}s"},
                status=429,
                headers={"Retry-After": str(retry)},
            )
        bucket.append(now)
        return await handler(request)

    return rate_limit_middleware
