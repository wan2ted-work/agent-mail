"""Shared helpers for API handlers: uniform error responses and a decorator that
removes the repetitive UUID-parsing + try/except boilerplate from every handler.
"""

from __future__ import annotations

import functools
import logging
from typing import Optional
from uuid import UUID

from aiohttp import web
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def json_error(error: str, status: int, detail: Optional[str] = None) -> web.Response:
    """Build a consistent error response. `detail` is only for client-safe messages."""
    body = {"error": error}
    if detail is not None:
        body["detail"] = detail
    return web.json_response(body, status=status)


def serialize(model: type[BaseModel], obj) -> dict:
    """Validate an ORM object against a pydantic model and dump to JSON-able dict."""
    return model.model_validate(obj).model_dump(mode="json")


class ApiError(Exception):
    """Raise from a handler to return a controlled error response."""

    def __init__(self, error: str, status: int = 400, detail: Optional[str] = None):
        super().__init__(error)
        self.error = error
        self.status = status
        self.detail = detail


def api_handler(require_secret: bool = True):
    """Wrap an aiohttp handler with uniform error handling.

    - If `require_secret`, parse `{secret}` into a UUID and stash it at
      `request["secret_uuid"]`, returning 400 on a malformed value.
    - Map `ApiError` -> its status, `ValidationError`/`ValueError` -> 400, and any
      other exception -> a generic 500 (the real cause is logged, never leaked).
    """

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(request: web.Request) -> web.Response:
            if require_secret:
                try:
                    request["secret_uuid"] = UUID(request.match_info["secret"])
                except (ValueError, KeyError):
                    return json_error("Invalid secret format (must be UUID)", 400)
            try:
                return await fn(request)
            except ApiError as e:
                return json_error(e.error, e.status, e.detail)
            except ValidationError as e:
                return json_error("Validation error", 400, detail=str(e))
            except ValueError as e:
                return json_error("Validation error", 400, detail=str(e))
            except Exception:
                logger.exception("Unhandled error in %s", fn.__name__)
                return json_error("Internal server error", 500)

        return wrapper

    return decorator
