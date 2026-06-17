# Agent Mail — Backend

Async REST API (aiohttp + SQLAlchemy 2 + asyncpg) that polls a Maildir, parses and
routes incoming email to instances, and serves the API consumed by the web UI and the
MCP server.

## Run

```bash
cp .env.example .env          # set DATABASE_URL, EMAIL_DOMAIN, MAIL_HOST, ...
pip install -r requirements.txt
python main.py                # listens on $HOST:$PORT (default 0.0.0.0:8080)
```

Or via the root `docker compose up` (recommended — brings up PostgreSQL too).

## Layout

```
app/
  api/        HTTP handlers + routes + pydantic schemas + helpers (api_handler)
  models/     SQLAlchemy models: Instance, InstanceKey, InstanceDomain, Email
  services/   email_parser (Maildir → DB), instance_service (CRUD + MX verify)
  workers.py  EmailMonitorWorker — polls MAILDIR_PATH every POLL_INTERVAL seconds
  security.py admin-token + rate-limit middleware
  config.py   env-driven settings
  database.py async engine + session
main.py       app entrypoint (CORS, startup/cleanup, worker task)
```

## Docs

- API reference: [`../docs/api.md`](../docs/api.md)
- Architecture: [`../docs/architecture.md`](../docs/architecture.md)
- Security: [`../docs/security.md`](../docs/security.md)

Configuration is documented in [`.env.example`](.env.example).
