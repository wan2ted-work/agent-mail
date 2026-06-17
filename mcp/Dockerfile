FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY agent_mail_mcp ./agent_mail_mcp

RUN pip install --no-cache-dir .

# MCP servers speak over stdio by default.
ENTRYPOINT ["agent-mail-mcp"]
