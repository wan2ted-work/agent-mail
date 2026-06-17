#!/usr/bin/env bash
# Agent Mail — the common flow as curl commands.
# Usage: API=http://localhost:8080 DOMAIN=example.com ./examples/curl-recipes.sh
set -euo pipefail

API="${AGENT_MAIL_API_URL:-${API:-http://localhost:8080}}"
DOMAIN="${AGENT_MAIL_EMAIL_DOMAIN:-${DOMAIN:-example.com}}"

# 1. Generate a secret (any UUIDv4) — this is your credential. Keep it.
SECRET="$(cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c 'import uuid;print(uuid.uuid4())')"
echo "Secret: $SECRET"

# 2. Get/create the instance (GET auto-creates it).
curl -fsS "$API/api/instances/$SECRET" | jq .

# 3. Register a key. Mail to anything@<key>.$DOMAIN now routes here.
KEY="demo-$(date +%s 2>/dev/null || echo run)"
curl -fsS -X POST "$API/api/instances/$SECRET/keys" \
  -H 'Content-Type: application/json' \
  -d "{\"key\":\"$KEY\"}" | jq .
echo "Address: anything@$KEY.$DOMAIN"

# 4. List emails (newest first). Filters: from_email, subject, extracted_key, nickname.
curl -fsS "$API/api/instances/$SECRET/emails?limit=20" | jq '.total, .items'

# 5. Read one email by id (replace EMAIL_ID with an id from step 4).
# curl -fsS "$API/api/instances/$SECRET/emails/EMAIL_ID" | jq .

# 6. (Optional) Attach a custom domain and verify it (after setting its MX record).
# curl -fsS -X POST "$API/api/instances/$SECRET/domains" \
#   -H 'Content-Type: application/json' -d '{"domain":"acme.com"}' | jq .
# curl -fsS -X POST "$API/api/instances/$SECRET/domains/acme.com/verify" | jq .
