# Changelog

All notable changes to Agent Mail are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/) once it reaches 1.0.

## [0.1.0] — 2026-06-17

First public release. Merges the previously separate backend and frontend into a single
MIT-licensed monorepo, adds an MCP server for AI agents, full documentation, and security
hardening.

### Added
- **Backend** (aiohttp + PostgreSQL): Maildir-polling worker, recipient routing by
  subdomain key or MX-verified custom domain, REST API, orphaned-mail back-fill.
- **Frontend** (Vue 3 + Vite + Pinia + Tailwind): UUID-secret login, inbox with search
  and filters, key management, custom-domain verification UI. Fully domain-neutral.
- **MCP server**: thin wrapper over the REST API exposing `create_mailbox`,
  `list_emails`, `get_email`, `wait_for_email`, and custom-domain tools so AI agents can
  provision and read mail. Packaged for PyPI (`agent-mail-mcp`).
- **Docs**: architecture, getting-started (self-host with DNS + Postfix), security, API
  reference, MCP guide.
- **Agent-adoption assets**: `AGENTS.md`, `llms.txt`, runnable `examples/`, and a
  one-command `make demo` that seeds sample mail.
- One-command local stack via `docker compose` (with optional Postfix and MCP profiles).

### Security
- Subdomain keys are **scoped to their domain** — a key only matches mail on the shared
  `EMAIL_DOMAIN` or a verified custom domain owned by the same instance.
- Configurable CORS, optional `X-Admin-Token` gating, per-IP rate limiting, and email
  retention sweeps.
- Email HTML is sanitized with DOMPurify before rendering.
- Started from a clean history; no secrets or production values are present in the repo
  or its git history.

[0.1.0]: https://github.com/wan2ted-work/agent-mail/releases/tag/v0.1.0
