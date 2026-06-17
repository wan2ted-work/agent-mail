# Getting started

This guide covers running Agent Mail locally, the two deployment models, and the
DNS + Postfix setup needed to receive real mail when self-hosting.

## Two deployment models

Agent Mail can be run two ways. They are not mutually exclusive — the hosted tier is
just someone else self-hosting for you.

### 1. Managed (mypm.cloud) — zero infrastructure

You don't run anything. You use the hosted instance and get addresses immediately:

- **Instant inbox:** any address `anything@<key>.mypm.cloud` routes to the space that
  owns `<key>`. No DNS, no mail server.
- **Bring your own domain:** add your domain in the UI, point its MX record at
  `mail.mypm.cloud`, click verify. Mail to your domain now lands in your space.

Use this if you want addresses *now* and don't care about hosting the data yourself.

### 2. Self-hosted (this repo) — you own everything

You run the stack and a mail server. **This is the important difference to understand:**

> When you self-host, *how mail reaches your box is entirely your DNS + your mail
> server.* Agent Mail never "discovers" or connects to your server — it only reads the
> Maildir that **your** Postfix fills. You map a domain to your server by setting its
> **MX record to your server's IP** and configuring Postfix to accept and deliver that
> mail. That's the whole "domain mapping": a DNS record you control.

So the flow you set up is:

```
your DNS:  yourdomain.com   MX → mail.yourdomain.com → A → <your server IP>
your box:  Postfix accepts mail for yourdomain.com, delivers to Maildir
Agent Mail: polls that Maildir, routes by key/domain
```

Choose self-hosting if you need data ownership, private domains, or custom policy.

## Run locally (no mail server)

The fastest way to see it working. You won't receive *real* mail, but you can ingest
`.eml` files by hand.

```bash
git clone https://github.com/<you>/agent-mail.git
cd agent-mail
cp .env.example .env
# edit .env: set a real POSTGRES_PASSWORD and your EMAIL_DOMAIN
docker compose up --build
```

This starts:

| Service | URL |
|---------|-----|
| Frontend (web UI) | <http://localhost:8081> |
| Backend API | <http://localhost:8080> (`/health`) |
| PostgreSQL | internal |

### Ingest a test email

The backend polls `./maildir/new/`. Drop a raw RFC-822 message there:

```bash
cat > maildir/new/test1.eml <<'EOF'
From: Sender <sender@external.test>
To: signup@demo.example.com
Subject: Hello from Agent Mail
Message-ID: <test-1@external.test>
Date: Tue, 17 Jun 2026 12:00:00 +0000
Content-Type: text/plain; charset=utf-8

This is a test message body.
EOF
```

Within `POLL_INTERVAL` seconds it's ingested with `extracted_key = "demo"`. Open the
UI, get/create an instance, add the key `demo`, and the email links to your space.

> The `To:` here is `signup@demo.example.com`, so `EMAIL_DOMAIN=example.com` and the
> key is `demo`. Adjust to match your `.env`.

## Option A — containerized mail server (quickest path to real mail)

The compose file ships an optional Postfix container under the `mailserver` profile, so
the whole stack — including mail reception — comes up with one command:

```bash
docker compose --profile mailserver up -d --build
```

This Postfix accepts SMTP on **port 25** for `EMAIL_DOMAIN` as a catch-all and writes
into the same `./maildir` the backend polls.

> **What the container can't do for you.** Receiving *real* mail from the internet still
> requires things outside any container: a **public IP**, an **open inbound port 25**
> (many ISPs/clouds block it), and correct **DNS** — an `MX` record for your domain
> pointing at this host, plus `PTR`/`SPF`/`DKIM` so senders don't reject you. The
> container handles SMTP and delivery; you handle the network and DNS.

> **Maildir path note.** Different mail-server images lay out the Maildir slightly
> differently. The backend polls `MAILDIR_PATH` (the `new/` subdirectory). If mail lands
> but isn't ingested, check that the container's delivery path and the backend's
> `MAILDIR_PATH` point at the same `…/Maildir/new` directory, and adjust the volume
> mounts accordingly.

For production-grade mail (virtual domains, anti-spam, DKIM signing) consider
[docker-mailserver](https://docker-mailserver.github.io/) as the `mailserver` image, or
run Postfix on the host as described next.

## Option B — run Postfix on the host (self-host with Postfix)

### Step 1 — DNS

Point your domain at your server. Subdomain-key addresses are `x@<key>.yourdomain.com`
(the key is a **single label** directly under your `EMAIL_DOMAIN`), so you want a
wildcard MX so any `<key>.yourdomain.com` is accepted:

```
mail.yourdomain.com.       A     <your server IP>
yourdomain.com.            MX    10 mail.yourdomain.com.
*.yourdomain.com.          MX    10 mail.yourdomain.com.   ; wildcard so every key resolves
```

Set `EMAIL_DOMAIN=yourdomain.com`, `MAIL_HOST=mail.yourdomain.com`,
`MAIL_SERVER_IP=<your server IP>` in `.env`. With this, `anything@<key>.yourdomain.com`
routes by `<key>` — e.g. `otp@acme.yourdomain.com` → key `acme`.

### Step 2 — Postfix (catch-all → Maildir)

Install Postfix and configure it to accept all mail for your domain and deliver to a
single Maildir (a "catch-all"). The essentials:

```ini
# /etc/postfix/main.cf  (illustrative — adapt to your setup)
myhostname = mail.yourdomain.com
mydestination = yourdomain.com
# Deliver everything for the domain to one Maildir:
luser_relay = vmail
local_recipient_maps =
home_mailbox = Maildir/
```

A common production pattern is virtual mailboxes with a catch-all alias:

```
# /etc/postfix/virtual
@yourdomain.com    vmail@localhost
```

The exact Postfix config depends on your distro and whether you use virtual domains.
The only requirement Agent Mail cares about: **new messages end up as files in the
directory you set as `MAILDIR_PATH`** (default `/root/Maildir/new`, mapped to
`./maildir/new` in the compose file).

> Harden the mail server itself (TLS, SPF/DKIM/DMARC, spam filtering) — that's outside
> Agent Mail's scope but important for real use.

### Step 3 — Mount the Maildir into the backend

In `docker-compose.yml`, the backend mounts `./maildir/new` read-only. Point that at
the directory Postfix delivers to (e.g. bind-mount `/var/mail/vhosts/Maildir/new`):

```yaml
  backend:
    volumes:
      - /var/mail/vhosts/Maildir/new:/maildir/new:ro
```

### Step 4 — Bring it up

```bash
docker compose up -d --build
```

Send a message to `anything@<key>.yourdomain.com`, add that key in the UI, and watch
it arrive.

## Custom domains for your users

Once self-hosted, your users can attach their *own* domains:

1. They add the domain in the UI (`POST /api/instances/{secret}/domains`).
2. They create an MX record: `theirdomain.com MX 10 mail.yourdomain.com`.
3. They click **Verify** — the backend confirms the MX points at `MAIL_HOST`.
4. All mail to `theirdomain.com` now routes to their instance.

See [architecture.md](architecture.md#custom-domains--mx-verification) for how
verification works.

## Configuration reference

See the `.env.example` files (`./.env.example`, `backend/.env.example`,
`frontend/.env.example`) for every variable. The security-related ones
(`CORS_ALLOW_ORIGINS`, `ADMIN_API_TOKEN`, `RATE_LIMIT_PER_MINUTE`,
`EMAIL_RETENTION_DAYS`) are explained in [security.md](security.md).

## Production notes

- Put the stack behind a reverse proxy (Traefik/Caddy/nginx) terminating TLS.
- Set explicit `CORS_ALLOW_ORIGINS` (not `*`) once you know your frontend origin.
- Back up PostgreSQL; the `raw_email` column preserves the original message.
- Consider `EMAIL_RETENTION_DAYS` so disposable inboxes don't grow forever.
