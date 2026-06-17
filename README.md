<div align="center">

# 📬 Agent Mail

**Create disposable, programmable email inboxes on the fly — for humans and AI agents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Backend: aiohttp](https://img.shields.io/badge/backend-aiohttp-2c5bb4.svg)](backend)
[![Frontend: Vue 3](https://img.shields.io/badge/frontend-Vue%203-42b883.svg)](frontend)
[![MCP](https://img.shields.io/badge/MCP-enabled-purple.svg)](mcp)

</div>

---

Agent Mail turns any domain you control into an **endless supply of inboxes**. Send mail to
`anything@<key>.yourdomain.com` and it instantly appears in the space tied to that `key` —
no per-address setup, no mailbox provisioning. Point a whole custom domain at it and every
address on that domain lands in one place.

It ships with a **web UI** for humans and an **MCP server** so AI agents can provision their
own inboxes and read mail programmatically (e.g. to receive sign-up confirmations, OTPs, or
notifications during automated workflows).

## Why

- **On-the-fly addresses** — `report@acme.x.com`, `signup@acme.x.com`, `anything@acme.x.com`
  all route to the same space. Invent addresses as you go.
- **Agent-native** — the MCP server lets a Claude/LLM agent create a mailbox and poll it for
  the verification email it just triggered.
- **Self-hostable** — bring your own domain and mail server, own all the data. MIT licensed.
- **Or fully managed** — don't want to run a mail server? Use the hosted tier on `mypm.cloud`
  and skip straight to the addresses.

## How it works (60-second version)

Agent Mail does **not** speak SMTP/IMAP itself. A standard mail server (Postfix) receives mail
and drops it into a Maildir; Agent Mail's worker polls that directory, parses each message, and
routes it to the right space.

```
                                          ┌──────────────────────────────┐
  sender ──► MX of yourdomain.com ──► Postfix ──► Maildir/new/*.eml      │
                                          └───────────────┬──────────────┘
                                                          │ poll (every N s)
                                                          ▼
                                            ┌──────────────────────────┐
                                            │  Agent Mail backend       │
                                            │  • parse recipient        │
                                            │  • route by key / domain  │
                                            │  • store in PostgreSQL    │
                                            └─────────┬─────────┬───────┘
                                                      │ REST     │ REST
                                              ┌───────▼──┐   ┌───▼────────┐
                                              │ Web UI    │   │ MCP server │
                                              │ (Vue 3)   │   │ (agents)   │
                                              └───────────┘   └────────────┘
```

**Routing.** The recipient address decides the destination:

| Address pattern               | Routes by                          | Example                         |
|-------------------------------|------------------------------------|---------------------------------|
| `x@<KEY>.yourdomain.com`      | the **key** (a subdomain label)    | `otp@acme.example.com`          |
| `x@customdomain.com`          | a **verified custom domain**       | `otp@acme.com`                  |

Each "space" is an **instance**, identified by a secret UUID. Add keys/domains to an instance,
and matching mail flows in. Mail that arrives before a key exists is stored as *orphaned* and
auto-linked the moment you register the matching key.

> See **[docs/architecture.md](docs/architecture.md)** for the full data model and request flow.

## Repository layout

| Path          | What it is                                                              |
|---------------|------------------------------------------------------------------------|
| `backend/`    | aiohttp + PostgreSQL API and the Maildir polling worker (Python 3.10)   |
| `frontend/`   | Vue 3 + Vite + Pinia + Tailwind web client                              |
| `mcp/`        | Model Context Protocol server exposing mailbox tools to AI agents       |
| `docs/`       | Architecture, setup, security, API and MCP guides                       |
| `docker-compose.yml` | One-command local stack (db + backend + frontend [+ mcp])       |

## Quick start (local)

```bash
git clone https://github.com/<you>/agent-mail.git
cd agent-mail
cp .env.example .env            # set POSTGRES_PASSWORD, EMAIL_DOMAIN, ...
docker compose up --build       # db + backend + frontend
```

- Web UI: <http://localhost:8081>
- API: <http://localhost:8080> (`GET /health` to check)

No mail server yet? Drop a raw `.eml` file into `maildir/new/` and it'll be ingested within
`POLL_INTERVAL` seconds. To receive real mail, point a domain's MX at your Postfix and have it
deliver to the same Maildir — full walkthrough in **[docs/getting-started.md](docs/getting-started.md)**.

## Using it with an AI agent (MCP)

The MCP server lets an agent provision and read mail without touching the UI:

```jsonc
// Claude Code / Claude Desktop MCP config
{
  "mcpServers": {
    "agent-mail": {
      "command": "python",
      "args": ["-m", "agent_mail_mcp"],
      "env": {
        "AGENT_MAIL_API_URL": "http://localhost:8080",
        "AGENT_MAIL_EMAIL_DOMAIN": "example.com"
      }
    }
  }
}
```

Then an agent can call `create_mailbox`, get back `signup@<key>.example.com`, trigger a flow
that mails that address, and `list_emails` / `get_email` to read the result. See
**[docs/mcp.md](docs/mcp.md)**.

## Documentation

- **[Architecture](docs/architecture.md)** — components, data model, routing internals
- **[Getting started / self-hosting](docs/getting-started.md)** — DNS, Postfix, deploy
- **[Security](docs/security.md)** — threat model and hardening checklist
- **[API reference](docs/api.md)** — every endpoint, with request/response shapes
- **[MCP server](docs/mcp.md)** — tools, configuration, agent recipes

## Deployment models

| | **Managed (mypm.cloud)** | **Self-hosted (this repo)** |
|---|---|---|
| Run a mail server? | No | Yes (Postfix or similar) |
| Get an address | `x@<key>.mypm.cloud` instantly | `x@<key>.yourdomain.com` after MX setup |
| Custom domain | Point MX at `mail.mypm.cloud`, verify | Point MX at your own server |
| Data ownership | Hosted | Entirely yours |

The managed tier exists so people can use Agent Mail **without deploying anything**. Self-hosting
gives you full control — your DNS, your mail server, your database. See
[docs/getting-started.md](docs/getting-started.md#two-deployment-models) for the trade-offs.

## Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 wan2ted
