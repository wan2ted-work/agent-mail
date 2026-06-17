#!/usr/bin/env python3
"""End-to-end Agent Mail flow using the REST API (standard library only).

Provisions a mailbox, waits for an email to arrive at it, and extracts a numeric code.
This mirrors what the MCP `wait_for_email` tool does, in plain Python so you can see the
moving parts. Run the stack first (`docker compose up`), then:

    python examples/otp_flow.py

Override the backend with AGENT_MAIL_API_URL / the domain with AGENT_MAIL_EMAIL_DOMAIN.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import uuid

API_URL = os.environ.get("AGENT_MAIL_API_URL", "http://localhost:8080").rstrip("/")
EMAIL_DOMAIN = os.environ.get("AGENT_MAIL_EMAIL_DOMAIN", "example.com")


def _request(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API_URL}/api{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise SystemExit(f"{method} {path} failed: {e.code} {detail}")


def create_mailbox(key: str):
    """Create an instance (secret) and register a key; return (secret, address)."""
    secret = str(uuid.uuid4())
    _request("GET", f"/instances/{secret}")  # auto-creates the instance
    _request("POST", f"/instances/{secret}/keys", {"key": key})
    return secret, f"otp@{key}.{EMAIL_DOMAIN}"


def wait_for_email(secret: str, timeout: int = 120, interval: int = 5):
    """Poll until at least one email exists; return the newest one's full content."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        listing = _request("GET", f"/instances/{secret}/emails?limit=1")
        items = listing.get("items", [])
        if items:
            return _request("GET", f"/instances/{secret}/emails/{items[0]['id']}")
        time.sleep(interval)
    return None


def main():
    key = f"demo-{uuid.uuid4().hex[:8]}"
    secret, address = create_mailbox(key)
    print(f"Mailbox ready. Send mail to: {address}")
    print(f"Instance secret (keep this!): {secret}")
    print("Waiting for an email (deliver one, or drop a .eml into maildir/new/) ...")

    email = wait_for_email(secret, timeout=120, interval=5)
    if not email:
        print("Timed out waiting for mail.", file=sys.stderr)
        sys.exit(1)

    print(f"\nGot: {email['subject']!r} from {email['from_email']}")
    body = email.get("body_text") or ""
    match = re.search(r"\b(\d{4,8})\b", body)  # naive OTP extraction
    if match:
        print(f"Extracted code: {match.group(1)}")
    else:
        print("No numeric code found; full text body:\n")
        print(body)


if __name__ == "__main__":
    main()
