# Examples

Runnable examples for using Agent Mail from agents and scripts.

| File | What it shows |
|------|---------------|
| [`mcp-config.json`](mcp-config.json) | Drop-in MCP server config for Claude Desktop / Claude Code |
| [`otp_flow.py`](otp_flow.py) | End-to-end Python: create a mailbox, wait for an email, extract a code (REST API, stdlib-only) |
| [`curl-recipes.sh`](curl-recipes.sh) | The common flow as copy-paste `curl` commands |

All examples target a backend at `http://localhost:8080` by default (override with the
`AGENT_MAIL_API_URL` env var). Bring the stack up first:

```bash
docker compose up --build      # from the repo root
```

To exercise the flow without a real mail server, drop a `.eml` file into `maildir/new/`
(see [docs/getting-started.md](../docs/getting-started.md#ingest-a-test-email)).
