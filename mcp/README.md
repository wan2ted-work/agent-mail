# Agent Mail — MCP server

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets AI agents
create disposable inboxes and read mail. It is a **thin wrapper over the Agent Mail
REST API** — every tool is one or two HTTP calls to the backend, no extra server-side
logic. Point it at any Agent Mail backend over HTTP(S) (managed or self-hosted).

## Install & run

```bash
pip install .                 # from this directory
AGENT_MAIL_API_URL=https://email-api.example.com agent-mail-mcp
```

Or `python -m agent_mail_mcp`. The server speaks MCP over stdio.

## Configuration

| Env var | Default | Meaning |
|---------|---------|---------|
| `AGENT_MAIL_API_URL` | `http://localhost:8080` | Backend base URL (managed or self-hosted) |
| `AGENT_MAIL_EMAIL_DOMAIN` | `example.com` | Base domain for `anything@<key>.<domain>` |
| `AGENT_MAIL_ADMIN_TOKEN` | — | Optional `X-Admin-Token`, if the backend requires one |

## Wire it into a client

Claude Desktop / Claude Code (`mcpServers` config):

```jsonc
{
  "mcpServers": {
    "agent-mail": {
      "command": "agent-mail-mcp",
      "env": {
        "AGENT_MAIL_API_URL": "https://email-api.example.com",
        "AGENT_MAIL_EMAIL_DOMAIN": "example.com"
      }
    }
  }
}
```

## Tools

| Tool | Maps to | Purpose |
|------|---------|---------|
| `create_mailbox` | `GET /instances/{s}` + `POST .../keys` | Make a mailbox, return an address + secret |
| `get_mailbox` | `GET /instances/{s}` | Inspect an instance (keys, domains) |
| `add_key` / `remove_key` | `POST` / `DELETE .../keys` | Manage subdomain keys |
| `list_emails` | `GET .../emails` | List received mail (with filters) |
| `get_email` | `GET .../emails/{id}` | Read a full message |
| `wait_for_email` | polls `GET .../emails` | Block until a matching mail arrives |
| `add_custom_domain` / `verify_custom_domain` / `list_custom_domains` | `.../domains` | Manage custom domains |

See [`../docs/mcp.md`](../docs/mcp.md) for agent recipes and the full flow.
