# Contributing to Agent Mail

Thanks for your interest in improving Agent Mail! This is a small, self-hostable email
service — contributions of all sizes are welcome.

## Project layout

| Path | What |
|------|------|
| `backend/` | aiohttp + PostgreSQL API + Maildir worker (Python 3.10+) |
| `frontend/` | Vue 3 + Vite web client |
| `mcp/` | MCP server (Python) wrapping the REST API |
| `docs/` | All documentation (mkdocs) |

## Getting set up

```bash
git clone https://github.com/<you>/agent-mail.git
cd agent-mail
cp .env.example .env          # set a real POSTGRES_PASSWORD
docker compose up --build
```

For component-level work, see the README in each directory. You can also run pieces
natively:

```bash
# backend
cd backend && pip install -r requirements.txt && python main.py
# frontend
cd frontend && npm install && npm run dev
# mcp
cd mcp && pip install . && agent-mail-mcp
```

## Making changes

1. **Branch** off `main`.
2. Keep changes focused; one logical change per PR.
3. **Match the surrounding style** — the backend is plain async Python, the frontend is
   Vue 3 `<script setup>`. No new heavyweight dependencies without discussion.
4. Update **docs** when you change behavior (especially `docs/api.md` for API changes
   and `docs/security.md` for anything touching the trust model).
5. Don't commit secrets. `.env` is git-ignored; only `.env.example` (placeholders) is
   tracked.

## Before opening a PR

- [ ] `cd frontend && npm run build` succeeds.
- [ ] Backend modules import/compile (`python -m py_compile` over changed files; run the
      app locally if you touched request handling).
- [ ] Docs updated for any user-visible or API change.
- [ ] No secrets, real domains, or IPs added to tracked files.

## Reporting bugs & ideas

Open an issue using the templates. For **security vulnerabilities**, do **not** open a
public issue — follow [SECURITY.md](SECURITY.md).

## Code of conduct

Be respectful and constructive. We follow the spirit of the
[Contributor Covenant](https://www.contributor-covenant.org/).

## License

By contributing, you agree your contributions are licensed under the project's
[MIT License](LICENSE).
