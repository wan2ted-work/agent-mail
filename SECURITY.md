# Security Policy

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, report them privately via one of:

- GitHub's **[Private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)**
  (the "Report a vulnerability" button under the repository's *Security* tab), or
- email to the maintainer.

Please include:

- a description of the vulnerability and its impact,
- steps to reproduce (a proof of concept if possible),
- affected component (`backend`, `frontend`, `mcp`) and version/commit.

We aim to acknowledge reports within a few days and will keep you updated on the fix.
Please give us reasonable time to address the issue before any public disclosure.

## Scope & known design notes

Agent Mail's trust model and known weaknesses (and how to harden against them) are
documented in **[docs/security.md](docs/security.md)**. In particular:

- The instance **secret UUID is a bearer credential** — protect it like a password.
- Email HTML is **attacker-controlled**; it is sanitized with DOMPurify before render.
- Several protections are **opt-in** (`ADMIN_API_TOKEN`, explicit `CORS_ALLOW_ORIGINS`,
  `RATE_LIMIT_PER_MINUTE`, `EMAIL_RETENTION_DAYS`) — enable them in production.

Before reporting, please check `docs/security.md` to see whether the behavior is a known,
documented trade-off with a configuration mitigation.

## Supported versions

This project is pre-1.0; security fixes land on `main`. Run a recent commit.
