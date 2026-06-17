# Agent Mail

**Create disposable, programmable email inboxes on the fly — for humans and AI agents.**

Send mail to `anything@<key>.yourdomain.com` and it instantly appears in the space tied
to that key. Point a whole custom domain at it and every address on that domain lands in
one place. A web UI serves humans; an MCP server lets AI agents provision and read mail
programmatically.

## Start here

- **[Architecture](architecture.md)** — how the pieces fit and how mail is routed.
- **[Getting started](getting-started.md)** — run locally, then self-host with DNS + Postfix.
- **[Security](security.md)** — trust model, known weaknesses, hardening checklist.
- **[API reference](api.md)** — every endpoint, with examples.
- **[MCP server](mcp.md)** — tools and agent recipes.

## In one diagram

```
sender ──► MX ──► Postfix ──► Maildir ──► backend (poll + route) ──► PostgreSQL
                                                │
                                          ┌─────┴─────┐
                                       Web UI      MCP server
                                      (humans)     (AI agents)
```

See the [README](https://github.com/<you>/agent-mail) for the project overview.
