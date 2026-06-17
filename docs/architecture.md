# Architecture

Agent Mail is a small set of cooperating services. This document explains the
components, the data model, and exactly how an incoming email finds its way to a
user's space.

## Components

```
                      ┌──────────────────────────────────────────────┐
   Internet           │                  Your server(s)               │
                      │                                               │
  sender ──► DNS MX ──┼──► Postfix ──► Maildir/new/*.eml              │
                      │                       │                       │
                      │                       │ filesystem poll       │
                      │            ┌──────────▼───────────┐           │
                      │            │  backend (aiohttp)    │           │
                      │            │  ├─ worker (polls)    │           │
                      │            │  ├─ parser/router     │           │
                      │            │  └─ REST API          │           │
                      │            └─────┬───────────┬─────┘           │
                      │                  │ SQL        │ REST           │
                      │            ┌─────▼─────┐  ┌───▼──────────┐     │
                      │            │ PostgreSQL│  │ frontend (Vue)│    │
                      │            └───────────┘  │ + MCP server  │    │
                      │                           └───────────────┘    │
                      └──────────────────────────────────────────────┘
```

| Component | Tech | Responsibility |
|-----------|------|----------------|
| **backend** | aiohttp, SQLAlchemy 2 (async), asyncpg, pydantic | Poll Maildir, parse + route mail, serve the REST API |
| **PostgreSQL** | Postgres 16 + `pg_trgm` | Store instances, keys, domains, emails |
| **frontend** | Vue 3, Vite, Pinia, Tailwind | Human web client |
| **mcp** | Python MCP server | Expose mailbox tools to AI agents |
| **Postfix** | *(your responsibility)* | Receive SMTP, deliver to Maildir |

A key design choice: **the backend does not implement SMTP or IMAP.** It relies on
a real MTA (Postfix) to receive mail and deliver it to a Maildir directory, then
reads that directory. This keeps the service simple and lets you reuse a
battle-tested mail stack for the hard parts (spam, TLS, delivery).

## Data model

Four tables, all owned by an **instance** (a "space").

```
Instance (id = secret UUID)
  │  description, is_active, created_at, updated_at
  │
  ├─< InstanceKey      (id, instance_id, key UNIQUE, created_at)
  │       key is a subdomain label: anything@<key>.<domain>
  │
  ├─< InstanceDomain   (id, instance_id, domain UNIQUE, is_verified, verified_at, created_at)
  │       a full custom domain, verified by MX record
  │
  └─< Email            (id, instance_id NULLABLE, extracted_key, message_id UNIQUE,
                        from_email, from_name, to_email, subject,
                        body_text, body_html, raw_email, filename, received_at, created_at)
```

Notes:
- **`Instance.id` is the secret.** There is no separate user table or password —
  whoever holds the UUID controls the instance. (See [security.md](security.md) for
  why and how to harden this.)
- **`InstanceKey.key` and `InstanceDomain.domain` are globally unique.** Two
  instances can't both claim the same key or domain.
- **`Email.instance_id` is nullable.** Mail that matches no key/domain yet is stored
  *orphaned* (`instance_id = NULL`) and back-filled later — see
  [Orphaned mail](#orphaned-mail).
- **`Email.message_id` is unique**, making ingestion idempotent: re-parsing the same
  file never duplicates a row.
- `from_email` and `subject` have **GIN + `pg_trgm`** indexes for fuzzy search.

## The flow of an incoming email

1. **Delivery.** A sender's MTA looks up the MX record for the recipient domain and
   delivers the message to your Postfix, which writes it as a file into
   `Maildir/new/`.
2. **Polling.** The backend's `EmailMonitorWorker` lists `MAILDIR_PATH` every
   `POLL_INTERVAL` seconds and processes new files
   (`backend/app/workers.py`).
3. **Parsing.** `EmailParserService.parse_email_file` reads headers and body
   (multipart-aware), preferring `X-Original-To` over `To` for the recipient
   (`backend/app/services/email_parser.py`).
4. **Routing.** `parse_recipient` resolves the recipient into a routing identity
   using the public-suffix list (offline `tldextract`):
   - `x@<KEY>.example.com` → subdomain present → route by **key** = the label next to
     the registrable domain.
   - `x@acme.com` → bare registrable domain → route by **verified custom domain**.
5. **Storage.** `save_email` looks up the owning instance (a verified `InstanceDomain`
   for bare addresses, or an `InstanceKey` for subdomain addresses) and inserts the
   `Email`. If no owner is found, `instance_id` stays `NULL`.

### Routing in detail

| Recipient                     | `tldextract` | Routed by | Matches |
|-------------------------------|--------------|-----------|---------|
| `otp@acme.example.com`        | subdomain=`acme`, registrable=`example.com` → key = `acme` | `InstanceKey.key == "acme"` scoped to domain `example.com` | the instance that registered key `acme` |
| `otp@acme.com`                | subdomain=``, registrable=`acme.com` | verified `InstanceDomain.domain == "acme.com"` | instance that verified `acme.com` |

> **Security note on subdomain keys.** A subdomain route is **scoped to its parent
> domain**: it matches only when the parent registrable domain is the shared
> `EMAIL_DOMAIN`, or a *verified* custom domain owned by the same instance. This stops a
> key registered under one domain from capturing mail that arrived on another. See
> [security.md](security.md#key-scoping).

### Orphaned mail

Mail often arrives *before* the user has registered the matching key (e.g. a sign-up
confirmation racing the UI). Such mail is stored with `instance_id = NULL` and
`extracted_key` set. When a key is later added, `InstanceService` updates all orphaned
emails whose `extracted_key` matches, linking them to the new instance
(`backend/app/services/instance_service.py`). Domain verification does the same for
bare-domain mail. The `GET /api/emails/orphaned` endpoint exposes the unrouted pile
(intended for operators/debugging — note it is **not** instance-scoped; see
[security.md](security.md)).

## Custom domains & MX verification

A user can attach a full domain to their instance:

1. `POST /api/instances/{secret}/domains` registers `acme.com` (unverified).
2. The user adds an MX record for `acme.com` pointing at `MAIL_HOST`.
3. `POST /api/instances/{secret}/domains/{domain}/verify` performs a DNS-over-HTTPS
   lookup (`https://dns.google/resolve`) and marks the domain verified if its MX
   points at `MAIL_HOST` (or resolves to `MAIL_SERVER_IP`)
   (`backend/app/services/instance_service.py`).
4. Once verified, bare mail to `acme.com` routes to that instance.

Verification doubles as proof of control **and** a functional check: if the MX points
at your server, mail genuinely arrives there.

## Request lifecycle (API)

The API is stateless. Every request to an instance route carries the secret UUID in
the path; the handler validates the UUID, loads the instance (auto-creating it on
`GET`), and serves the request. CORS is configurable. See [api.md](api.md) for the
full endpoint list and [security.md](security.md) for the auth model.

## Configuration surface

All configuration is environment-driven (`backend/app/config.py`,
`frontend/src/config.js`). The important knobs:

| Var | Side | Meaning |
|-----|------|---------|
| `DATABASE_URL` | backend | Async Postgres DSN |
| `MAILDIR_PATH` | backend | Directory the worker polls |
| `EMAIL_DOMAIN` | both | Base domain for subdomain-key addresses |
| `MAIL_HOST` / `MAIL_SERVER_IP` | backend | MX target for custom-domain verification |
| `POLL_INTERVAL` | backend | Seconds between Maildir scans |
| `VITE_API_URL` | frontend | Where the UI finds the API |
| `CORS_ALLOW_ORIGINS`, `ADMIN_API_TOKEN`, `RATE_LIMIT_PER_MINUTE`, `EMAIL_RETENTION_DAYS` | backend | Hardening — see [security.md](security.md) |

Continue to **[getting-started.md](getting-started.md)** to stand it all up.
