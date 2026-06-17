# Agent Mail — Frontend

Vue 3 + Vite + Pinia + Tailwind web client. UUID-secret login, inbox with search and
filters, key management, and custom-domain verification UI.

## Run

```bash
cp .env.example .env          # set VITE_API_URL, VITE_EMAIL_DOMAIN, ...
npm install
npm run dev                   # http://localhost:5173
```

Production build (served by nginx in the Docker image):

```bash
npm run build                 # outputs dist/
```

## Configuration

All runtime config is centralized in [`src/config.js`](src/config.js), sourced from
Vite env vars (baked in at build time):

| Var | Meaning |
|-----|---------|
| `VITE_API_URL` | Backend API base URL |
| `VITE_EMAIL_DOMAIN` | Base domain shown for `anything@<key>.<domain>` |
| `VITE_MAIL_HOST` | MX target shown in the custom-domain verify UI |
| `VITE_ALLOWED_HOSTS` | Optional dev-server host allowlist |

The UI is **domain-neutral** — nothing is hardcoded to a specific deployment.

## Layout

```
src/
  components/   AuthForm, InstanceInfo, EmailList, EmailDetail, SearchFilters, CustomDomains
  stores/       appStore.js (Pinia: secret, instance, emails, filters, pagination)
  services/     api.js (axios client)
  utils/        emailHeaders.js (RFC 2047 decoding)
  config.js     env-driven runtime config
```

See [`../docs/`](../docs/) for full documentation.
