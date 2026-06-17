# Security

Agent Mail handles email — often the kind used for sign-ups, OTPs, and password
resets. That makes the inbox a sensitive target. This document describes the trust
model, the known weaknesses in the current design, and a concrete hardening checklist.

> If you find a vulnerability, please follow [SECURITY.md](../SECURITY.md) for
> responsible disclosure rather than opening a public issue.

## Trust model

- An **instance** is identified by a **secret UUID** (`Instance.id`). Possession of
  the UUID grants full read/write access to that instance — there is no separate
  password or token by default.
- `GET /api/instances/{secret}` **auto-creates** the instance if it doesn't exist.
  Combined with UUIDv4's ~122 bits of entropy, guessing a live secret is infeasible,
  but the secret is a **bearer credential**: anyone who sees it (logs, referrer
  headers, screenshots, shared URLs) gains access.
- Routing keys and custom domains are **globally unique** and effectively
  first-come-first-served.

This model is convenient (no accounts, instant provisioning) but it pushes all the
security weight onto keeping the UUID secret and onto the hardening controls below.

## Known weaknesses & mitigations

### 1. Subdomain keys are scoped to their domain {#key-scoping}

**Issue (historical).** Originally `parse_recipient` routed `x@<KEY>.anydomain.com` by
the key alone and ignored the parent domain. Whoever registered key `acme` first
received *all* mail to `*@acme.<any domain pointed at the server>` — letting one tenant
claim a key another expected to use.

**Fixed.** A subdomain-key route now matches only when the parent registrable domain is
the shared `EMAIL_DOMAIN` **or** a *verified* `InstanceDomain` owned by the same
instance that holds the key (`backend/app/services/email_parser.py`,
`save_email`). The orphan back-fill on `add_key` is likewise restricted to mail that
arrived on the shared `EMAIL_DOMAIN` (`backend/app/services/instance_service.py`); mail
on a custom domain is claimed only through domain verification, which proves ownership.
The net effect: a key cannot capture mail from a domain the instance hasn't proven it
controls.

### 2. The secret travels in the URL path

**Issue.** Because the secret is in the path, it can leak via proxy logs, browser
history, and `Referer` headers.

**Mitigation.**
- Always serve the API over HTTPS (TLS terminated at your reverse proxy).
- Configure your proxy to **not log full request paths** for `/api/instances/*`.
- Enable the optional `ADMIN_API_TOKEN` (below) so that even a leaked instance secret
  can't perform admin/mutating actions without the second factor.
- Don't put the secret in links you share; the UI stores it in `localStorage`, not in
  the URL.

### 3. `GET /api/emails/orphaned` is not instance-scoped

**Issue.** The orphaned-mail endpoint returns unrouted mail across the whole
deployment (`backend/app/api/routes.py`). It's useful for operators but exposes mail
that hasn't been claimed yet.

**Mitigation.** Protect it behind `ADMIN_API_TOKEN` (or block it at the proxy) in any
multi-user deployment. It is intended for operator/debugging use only.

### 4. Open CORS

**Issue.** The stock backend enabled CORS for all origins with credentials
(`main.py`). With a bearer-style credential this is risky.

**Mitigation.** Set `CORS_ALLOW_ORIGINS` to the explicit origin(s) of your frontend.
Avoid `*` in production, especially together with `allow_credentials`.

### 5. Stored HTML email is attacker-controlled

**Issue.** `body_html` is whatever the sender sent. The email-detail view historically
did only naive `<script>` stripping (`frontend/src/components/EmailDetail.vue`), which
is **not** sufficient against XSS (e.g. `onerror=`, `javascript:` URLs, SVG payloads).

**Mitigation.** Sanitize HTML with a real sanitizer (DOMPurify) before rendering, or
render in a sandboxed iframe. Treat every rendered message as hostile.

### 6. No rate limiting

**Issue.** Nothing throttles requests, so the API is exposed to brute force and abuse.

**Mitigation.** Set `RATE_LIMIT_PER_MINUTE` and/or rate-limit at the reverse proxy.

### 7. Unbounded retention

**Issue.** Disposable inboxes accumulate mail (including `raw_email`) forever.

**Mitigation.** Set `EMAIL_RETENTION_DAYS` to purge old messages and limit blast radius
if the database is ever exposed.

## Hardening checklist

Configuration (see `.env.example`):

- [ ] `DATABASE_URL` uses a strong, unique password; the DB is not internet-exposed.
- [ ] `CORS_ALLOW_ORIGINS` set to explicit frontend origin(s), not `*`.
- [ ] `ADMIN_API_TOKEN` set; required for admin/mutating and orphaned-mail endpoints.
- [ ] `RATE_LIMIT_PER_MINUTE` set to a sane value.
- [ ] `EMAIL_RETENTION_DAYS` set if inboxes are disposable.

Deployment:

- [ ] All traffic over HTTPS; HSTS enabled.
- [ ] Reverse proxy does not log secrets in `/api/instances/*` paths.
- [ ] `GET /api/emails/orphaned` blocked or token-gated for multi-user setups.
- [ ] Frontend sanitizes HTML email (DOMPurify) before rendering.
- [ ] Mail server has SPF/DKIM/DMARC and spam filtering (defends against spoofed
      sign-up confirmations landing in a space).
- [ ] Database backups are encrypted; access is least-privilege.

Operational:

- [ ] Secrets are never committed (`.env` is git-ignored; `.env.example` only holds
      placeholders). Rotate any credential that was ever committed.
- [ ] Dependencies are kept patched (`requirements.txt`, `package.json`).

## The `ADMIN_API_TOKEN` second factor

When `ADMIN_API_TOKEN` is set, mutating/admin endpoints additionally require the header
`X-Admin-Token: <value>`. This means a leaked instance secret alone cannot delete an
instance, register domains, or read the orphaned pile — the operator token is also
needed. Leave it empty only for local/dev (open mode). See [api.md](api.md) for which
endpoints enforce it.

## Reporting

See [SECURITY.md](../SECURITY.md) for how to report vulnerabilities privately.
