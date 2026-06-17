# Agent Mail — Backend API Reference

Agent Mail is an [aiohttp](https://docs.aiohttp.org/) REST API for receiving and
querying email tied to "instances". An instance is identified by a **secret
UUID**, and emails are routed to an instance via per-instance *keys* and
*custom domains*.

## Base URL

The base URL is configurable. By default the server listens on port `8080`
(`backend/app/config.py:11`), so the default base URL is:

```
http://localhost:8080
```

All application routes are mounted under `/api`. There is one additional
top-level route, `/health`, used for liveness checks
(`backend/app/api/routes.py:25-30`).

## Authentication

The auth model is **"possession of the secret = full access"**. The instance
secret is a UUID embedded directly in the request path
(e.g. `/api/instances/{secret}`). Anyone who knows an instance's secret UUID has
full read/write access to that instance, its keys, its domains, and its emails.
There is no separate bearer token by default.

> **Hardening note (if configured):** An optional `X-Admin-Token` header may be
> required for requests if the server is started with an `ADMIN_API_TOKEN`
> configured. This admin-token gating is being added as a hardening measure; if
> the server does **not** set `ADMIN_API_TOKEN`, no such header is required and
> the path-secret model above applies as-is. Treat `X-Admin-Token` as
> conditional ("if configured").

### Secret validation

Every instance-scoped endpoint validates that `{secret}` parses as a UUID. A
malformed secret returns `400` with:

```json
{ "error": "Invalid secret format (must be UUID)" }
```

## Endpoint summary

| Method   | Path                                                        | Purpose                                                            |
| -------- | ----------------------------------------------------------- | ----------------------------------------------------------------- |
| `GET`    | `/health`                                                   | Liveness check                                                     |
| `GET`    | `/api/instances/{secret}`                                   | Get an instance (**auto-creates** it if missing) + email count    |
| `PUT`    | `/api/instances/{secret}`                                   | Update an instance's description / active flag                    |
| `DELETE` | `/api/instances/{secret}`                                   | Delete an instance (orphans its emails)                           |
| `GET`    | `/api/instances/{secret}/keys`                              | List the instance's keys                                          |
| `POST`   | `/api/instances/{secret}/keys`                              | Add a key (auto-associates previously-orphaned emails)           |
| `DELETE` | `/api/instances/{secret}/keys/{key}`                        | Remove a key                                                      |
| `GET`    | `/api/instances/{secret}/domains`                           | List the instance's custom domains                               |
| `POST`   | `/api/instances/{secret}/domains`                           | Register a custom domain (returns the MX record to create)       |
| `POST`   | `/api/instances/{secret}/domains/{domain}/verify`           | Verify a domain via its MX record                                |
| `DELETE` | `/api/instances/{secret}/domains/{domain}`                  | Remove a custom domain                                            |
| `GET`    | `/api/instances/{secret}/emails`                            | List/search emails for an instance (paginated)                   |
| `GET`    | `/api/instances/{secret}/emails/{email_id}`                 | Get full detail for one email                                     |
| `GET`    | `/api/emails/orphaned`                                      | List/search emails not yet associated with any instance          |

### Common error envelope

All error responses share this shape (`ErrorResponse`,
`backend/app/api/schemas.py:114-116`):

```json
{ "error": "Human readable error", "detail": "optional extra detail" }
```

Unhandled exceptions return `500` with `error: "Internal server error"` and a
`detail` string.

---

## `GET /health`

Liveness probe. Always returns `200`.

**Response `200`:**

```json
{ "status": "ok" }
```

---

## `GET /api/instances/{secret}`

Fetch an instance by its secret UUID, together with the number of emails
associated with it.

**Important — auto-create:** If no instance exists for the given (valid) secret
UUID, the server **creates one automatically** and returns it with
`email_count: 0` (`backend/app/api/instances.py:96-120`). This is the canonical
way to provision a new instance — pick a UUID and `GET` it.

### Path params

| Name     | Type | Description                |
| -------- | ---- | -------------------------- |
| `secret` | UUID | Instance secret / identity |

### Response `200`

`InstanceResponse` fields plus an injected `email_count`
(`backend/app/api/schemas.py:50-65`, `backend/app/api/instances.py:127-130`):

```json
{
  "id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
  "description": null,
  "is_active": true,
  "created_at": "2026-06-17T09:14:22.512000",
  "updated_at": "2026-06-17T09:14:22.512000",
  "keys": [
    {
      "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "instance_id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
      "key": "myproject",
      "created_at": "2026-06-17T09:15:01.000000"
    }
  ],
  "domains": [],
  "email_count": 12
}
```

For a freshly auto-created instance, `keys` and `domains` are empty and
`email_count` is `0`.

### Errors

| Status | Condition                          |
| ------ | ---------------------------------- |
| `400`  | `secret` is not a valid UUID       |
| `500`  | Failed to create / internal error  |

---

## `PUT /api/instances/{secret}`

Update an instance's `description` and/or `is_active` flag.

### Path params

| Name     | Type | Description     |
| -------- | ---- | --------------- |
| `secret` | UUID | Instance secret |

### Request body (`InstanceUpdate`, `schemas.py:45-47`)

Both fields are optional.

```json
{
  "description": "Production mailbox for Acme",
  "is_active": true
}
```

### Response `200`

Returns the updated `InstanceResponse` (note: **no** `email_count` on this
endpoint, `backend/app/api/instances.py:176-178`):

```json
{
  "id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
  "description": "Production mailbox for Acme",
  "is_active": true,
  "created_at": "2026-06-17T09:14:22.512000",
  "updated_at": "2026-06-17T10:02:55.117000",
  "keys": [],
  "domains": []
}
```

### Errors

| Status | Condition                                   |
| ------ | ------------------------------------------- |
| `400`  | Invalid UUID, or body fails validation      |
| `404`  | `{ "error": "Instance not found" }`         |
| `500`  | Internal error                              |

> Note: unlike `GET`, `PUT` does **not** auto-create — it returns `404` if the
> instance does not exist (`backend/app/api/instances.py:162-166`).

---

## `DELETE /api/instances/{secret}`

Delete an instance.

> **Behavior — orphaning:** Deleting an instance does **not** delete its emails;
> the emails become *orphaned* (their `instance_id` is cleared) and remain
> queryable via `GET /api/emails/orphaned`.

### Path params

| Name     | Type | Description     |
| -------- | ---- | --------------- |
| `secret` | UUID | Instance secret |

### Response `200`

```json
{ "message": "Instance deleted successfully" }
```

### Errors

| Status | Condition                            |
| ------ | ------------------------------------ |
| `400`  | Invalid UUID                         |
| `404`  | `{ "error": "Instance not found" }`  |
| `500`  | `{ "error": "Failed to delete instance" }` / internal error |

---

## `GET /api/instances/{secret}/keys`

List all keys belonging to an instance.

### Path params

| Name     | Type | Description     |
| -------- | ---- | --------------- |
| `secret` | UUID | Instance secret |

### Response `200`

Array of `InstanceKeyResponse` (`schemas.py:12-19`):

```json
[
  {
    "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "instance_id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
    "key": "myproject",
    "created_at": "2026-06-17T09:15:01.000000"
  }
]
```

### Errors

| Status | Condition                           |
| ------ | ----------------------------------- |
| `400`  | Invalid UUID                        |
| `404`  | `{ "error": "Instance not found" }` |
| `500`  | Internal error                      |

---

## `POST /api/instances/{secret}/keys`

Add a public key to an instance. The key is the local-part / label used in
inbound email addresses (e.g. `myproject` in
`anything@myproject.example.com`, depending on routing).

> **Behavior — back-association:** When a key is added, any previously
> **orphaned** emails whose `extracted_key` equals the new key are
> automatically associated with this instance
> (`backend/app/services/instance_service.py:164-175`).

### Path params

| Name     | Type | Description     |
| -------- | ---- | --------------- |
| `secret` | UUID | Instance secret |

### Request body (`InstanceKeyCreate`, `schemas.py:8-9`)

```json
{ "key": "myproject" }
```

`key` is required, length 1–255.

### Response `201`

Returns the created `InstanceKeyResponse`:

```json
{
  "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "instance_id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
  "key": "myproject",
  "created_at": "2026-06-17T09:15:01.000000"
}
```

### Errors

| Status | Condition                                                                         |
| ------ | --------------------------------------------------------------------------------- |
| `400`  | Invalid UUID, body validation error, or `"Failed to add key (instance not found or key already exists)"` |
| `500`  | Internal error                                                                    |

> Note: a missing instance or duplicate key both surface as `400`
> (`backend/app/api/instances.py:262-266`), not `404`.

---

## `DELETE /api/instances/{secret}/keys/{key}`

Remove a key from an instance.

### Path params

| Name     | Type   | Description           |
| -------- | ------ | --------------------- |
| `secret` | UUID   | Instance secret       |
| `key`    | string | The key value to drop |

### Response `200`

```json
{ "message": "Key 'myproject' removed successfully" }
```

### Errors

| Status | Condition                                          |
| ------ | -------------------------------------------------- |
| `400`  | Invalid UUID                                       |
| `404`  | `{ "error": "Key not found for this instance" }`   |
| `500`  | Internal error                                     |

---

## `GET /api/instances/{secret}/domains`

List all custom domains registered for an instance.

### Path params

| Name     | Type | Description     |
| -------- | ---- | --------------- |
| `secret` | UUID | Instance secret |

### Response `200`

Array of `InstanceDomainResponse` (`schemas.py:27-36`) each augmented with a
`dns_record` block describing the MX record the user must create
(`backend/app/api/instances.py:26-36`):

```json
[
  {
    "id": "d0c1b2a3-4455-46e7-8899-aabbccddeeff",
    "instance_id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
    "domain": "acme.com",
    "is_verified": false,
    "created_at": "2026-06-17T11:00:00.000000",
    "verified_at": null,
    "dns_record": {
      "type": "MX",
      "name": "acme.com",
      "value": "mail.example.com",
      "priority": 10,
      "hint": "Point acme.com's MX to mail.example.com, then verify."
    }
  }
]
```

`dns_record.value` is the server's configured `MAIL_HOST`
(default `mail.example.com`, `backend/app/config.py:19`).

### Errors

| Status | Condition                           |
| ------ | ----------------------------------- |
| `400`  | Invalid UUID                        |
| `404`  | `{ "error": "Instance not found" }` |
| `500`  | Internal error                      |

---

## `POST /api/instances/{secret}/domains`

Register a custom domain for the instance. The domain starts out
**unverified**; the response includes the MX record you must publish before
verifying.

### Path params

| Name     | Type | Description     |
| -------- | ---- | --------------- |
| `secret` | UUID | Instance secret |

### Request body (`InstanceDomainCreate`, `schemas.py:23-24`)

```json
{ "domain": "acme.com" }
```

`domain` is required, length 3–255.

### Response `201`

Same `dns_record`-augmented shape as the list endpoint, for the single new
domain:

```json
{
  "id": "d0c1b2a3-4455-46e7-8899-aabbccddeeff",
  "instance_id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
  "domain": "acme.com",
  "is_verified": false,
  "created_at": "2026-06-17T11:00:00.000000",
  "verified_at": null,
  "dns_record": {
    "type": "MX",
    "name": "acme.com",
    "value": "mail.example.com",
    "priority": 10,
    "hint": "Point acme.com's MX to mail.example.com, then verify."
  }
}
```

### Errors

| Status | Condition                                                                                 |
| ------ | ----------------------------------------------------------------------------------------- |
| `400`  | Invalid UUID, body validation error, or `"Failed to add domain (instance not found, invalid, or domain already registered)"` |
| `500`  | Internal error                                                                            |

---

## `POST /api/instances/{secret}/domains/{domain}/verify`

Verify a registered custom domain.

> **Behavior — MX check via DNS-over-HTTPS:** Despite a stale "TXT" mention in
> the route/handler comments, verification checks the domain's **MX record**, not
> a TXT record. The server resolves the domain's MX (and, as a fallback, A
> records) using Google DNS-over-HTTPS and considers the domain verified only if
> the MX points to the configured `MAIL_HOST`
> (`backend/app/services/instance_service.py:277-332`). On successful
> verification, any orphaned emails whose `extracted_key` equals the domain are
> linked to the instance (`instance_service.py:336-343`).

### Path params

| Name     | Type   | Description                |
| -------- | ------ | -------------------------- |
| `secret` | UUID   | Instance secret            |
| `domain` | string | The domain to verify       |

### Request body

None.

### Response `200` — verified

Returned when the MX record now points to `MAIL_HOST`. `is_verified` is `true`
and `verified_at` is set:

```json
{
  "id": "d0c1b2a3-4455-46e7-8899-aabbccddeeff",
  "instance_id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
  "domain": "acme.com",
  "is_verified": true,
  "created_at": "2026-06-17T11:00:00.000000",
  "verified_at": "2026-06-17T11:20:33.000000",
  "dns_record": {
    "type": "MX",
    "name": "acme.com",
    "value": "mail.example.com",
    "priority": 10,
    "hint": "Point acme.com's MX to mail.example.com, then verify."
  }
}
```

### Response `202` — not yet verified

Returned when the MX record does **not** yet point to `MAIL_HOST`. Status is
`202` (Accepted, pending), `is_verified` stays `false`, and an extra `message`
field is included (`backend/app/api/instances.py:461-464`):

```json
{
  "id": "d0c1b2a3-4455-46e7-8899-aabbccddeeff",
  "instance_id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
  "domain": "acme.com",
  "is_verified": false,
  "created_at": "2026-06-17T11:00:00.000000",
  "verified_at": null,
  "dns_record": {
    "type": "MX",
    "name": "acme.com",
    "value": "mail.example.com",
    "priority": 10,
    "hint": "Point acme.com's MX to mail.example.com, then verify."
  },
  "message": "MX record not pointing to mail.example.com yet. Add the MX record and retry (DNS propagation can take a few minutes)."
}
```

### Errors

| Status | Condition                                            |
| ------ | ---------------------------------------------------- |
| `400`  | Invalid UUID                                         |
| `404`  | `{ "error": "Domain not found for this instance" }`  |
| `500`  | Internal error                                       |

---

## `DELETE /api/instances/{secret}/domains/{domain}`

Remove a custom domain from an instance.

### Path params

| Name     | Type   | Description     |
| -------- | ------ | --------------- |
| `secret` | UUID   | Instance secret |
| `domain` | string | The domain      |

### Response `200`

```json
{ "message": "Domain 'acme.com' removed successfully" }
```

### Errors

| Status | Condition                                           |
| ------ | --------------------------------------------------- |
| `400`  | Invalid UUID                                        |
| `404`  | `{ "error": "Domain not found for this instance" }` |
| `500`  | Internal error                                      |

---

## `GET /api/instances/{secret}/emails`

List emails for an instance, newest first (ordered by `received_at` descending),
with pagination and optional exact/partial filters
(`backend/app/api/emails.py:14-94`).

### Path params

| Name     | Type | Description     |
| -------- | ---- | --------------- |
| `secret` | UUID | Instance secret |

### Query params

| Name            | Type    | Default | Match    | Description                                                                                  |
| --------------- | ------- | ------- | -------- | -------------------------------------------------------------------------------------------- |
| `skip`          | integer | `0`     | —        | Offset for pagination                                                                         |
| `limit`         | integer | `50`    | —        | Page size                                                                                     |
| `from_email`    | string  | —       | exact    | Filter by sender address (`Email.from_email == value`)                                        |
| `nickname`      | string  | —       | prefix   | Matches the local-part of the recipient: `to_email LIKE '{nickname}@%'` (e.g. `arty.bond`)    |
| `extracted_key` | string  | —       | exact    | Filter by the routing key extracted from the recipient address                               |
| `subject`       | string  | —       | partial  | `subject LIKE '%{subject}%'`                                                                  |

### Response `200`

Paginated envelope (`total`, `skip`, `limit`, `items`) where each item is an
`EmailListResponse` (`schemas.py:87-98`, `emails.py:78-92`):

```json
{
  "total": 2,
  "skip": 0,
  "limit": 50,
  "items": [
    {
      "id": "7e2a1b9c-3d4e-4f50-a1b2-c3d4e5f60718",
      "from_email": "alice@example.org",
      "from_name": "Alice Example",
      "to_email": "arty.bond@myproject.example.com",
      "extracted_key": "myproject",
      "subject": "Welcome aboard",
      "received_at": "2026-06-17T08:30:00.000000",
      "has_instance": true
    },
    {
      "id": "9f8e7d6c-5b4a-4039-8281-7060504030201",
      "from_email": "bob@example.net",
      "from_name": null,
      "to_email": "arty.bond@myproject.example.com",
      "extracted_key": "myproject",
      "subject": null,
      "received_at": "2026-06-16T22:05:11.000000",
      "has_instance": true
    }
  ]
}
```

`has_instance` is `true` here because these emails belong to an instance.

### Errors

| Status | Condition                           |
| ------ | ----------------------------------- |
| `400`  | Invalid UUID                        |
| `404`  | `{ "error": "Instance not found" }` |
| `500`  | Internal error                      |

---

## `GET /api/instances/{secret}/emails/{email_id}`

Fetch the full content of a single email belonging to the instance.

### Path params

| Name       | Type   | Description                     |
| ---------- | ------ | ------------------------------- |
| `secret`   | UUID   | Instance secret                 |
| `email_id` | UUID   | Email identifier                |

### Response `200`

Full `EmailResponse` (`schemas.py:68-84`):

```json
{
  "id": "7e2a1b9c-3d4e-4f50-a1b2-c3d4e5f60718",
  "instance_id": "3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa",
  "extracted_key": "myproject",
  "message_id": "<CAF=abc123@mail.example.org>",
  "from_email": "alice@example.org",
  "from_name": "Alice Example",
  "to_email": "arty.bond@myproject.example.com",
  "subject": "Welcome aboard",
  "body_text": "Hi there,\n\nWelcome to the project!\n",
  "body_html": "<p>Hi there,</p><p>Welcome to the project!</p>",
  "filename": "20260617-083000-7e2a1b9c.eml",
  "received_at": "2026-06-17T08:30:00.000000",
  "created_at": "2026-06-17T08:30:02.345000"
}
```

### Errors

| Status | Condition                                                            |
| ------ | ------------------------------------------------------------------- |
| `400`  | Invalid UUID                                                        |
| `404`  | `{ "error": "Instance not found" }` or `{ "error": "Email not found" }` |
| `500`  | Internal error                                                      |

---

## `GET /api/emails/orphaned`

List emails that are **not** associated with any instance (their `instance_id`
is `NULL`). These arise when mail is received for a key/domain that no instance
has claimed yet, or after an instance is deleted. Same pagination and filters as
the instance email listing (`backend/app/api/emails.py:159-216`).

> This endpoint is **not** scoped to a secret and has no `{secret}` path param.

### Query params

Identical to `GET /api/instances/{secret}/emails`:
`skip` (default `0`), `limit` (default `50`), `from_email` (exact),
`nickname` (prefix on recipient local-part), `extracted_key` (exact),
`subject` (partial).

### Response `200`

Same paginated `EmailListResponse` envelope, but every item has
`has_instance: false` (`emails.py:204-213`):

```json
{
  "total": 1,
  "skip": 0,
  "limit": 50,
  "items": [
    {
      "id": "11112222-3333-4444-5555-666677778888",
      "from_email": "noreply@vendor.com",
      "from_name": "Vendor",
      "to_email": "signup@unclaimed.example.com",
      "extracted_key": "unclaimed",
      "subject": "Confirm your account",
      "received_at": "2026-06-15T14:00:00.000000",
      "has_instance": false
    }
  ]
}
```

### Errors

| Status | Condition      |
| ------ | -------------- |
| `500`  | Internal error |

---

## Common flow (curl)

Assumes `BASE=http://localhost:8080` and a chosen secret UUID. Pick any UUID for
your instance — the first `GET` provisions it.

```bash
BASE=http://localhost:8080
SECRET=3f4d2c10-9b8a-4f7e-bc21-2a0f6d1e88aa
```

**1. Create / get the instance** (auto-creates on first call):

```bash
curl -s "$BASE/api/instances/$SECRET"
```

**2. Add a routing key** (also back-associates any matching orphaned emails):

```bash
curl -s -X POST "$BASE/api/instances/$SECRET/keys" \
  -H 'Content-Type: application/json' \
  -d '{"key": "myproject"}'
```

**3. List emails for the instance** (newest first, with optional filters):

```bash
# all (first page)
curl -s "$BASE/api/instances/$SECRET/emails?skip=0&limit=50"

# filtered: by sender, recipient nickname, key, and subject substring
curl -s "$BASE/api/instances/$SECRET/emails?from_email=alice@example.org&nickname=arty.bond&extracted_key=myproject&subject=welcome"
```

**4. Get full detail for one email:**

```bash
EMAIL_ID=7e2a1b9c-3d4e-4f50-a1b2-c3d4e5f60718
curl -s "$BASE/api/instances/$SECRET/emails/$EMAIL_ID"
```

**(Optional) Custom domain flow:**

```bash
# register the domain (returns the MX record to publish)
curl -s -X POST "$BASE/api/instances/$SECRET/domains" \
  -H 'Content-Type: application/json' \
  -d '{"domain": "acme.com"}'

# after publishing the MX record, verify it
# -> 200 when the MX points to MAIL_HOST, 202 (with a message) if not yet
curl -s -X POST "$BASE/api/instances/$SECRET/domains/acme.com/verify"
```

> If the server is configured with `ADMIN_API_TOKEN`, add
> `-H "X-Admin-Token: <token>"` to each request above.
