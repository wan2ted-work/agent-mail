#!/usr/bin/env bash
# Seed a demo instance and a couple of sample emails so the stack has data to show.
# Sample mail is delivered by dropping .eml files into ./maildir/new (the worker ingests
# them within POLL_INTERVAL seconds), so this works even without a real mail server.
set -euo pipefail

API="${AGENT_MAIL_API_URL:-http://localhost:8080}"
DOMAIN="${AGENT_MAIL_EMAIL_DOMAIN:-example.com}"
SECRET="00000000-0000-4000-8000-000000000001"   # fixed demo secret
KEY="demo"
MAILDIR="$(cd "$(dirname "$0")/.." && pwd)/maildir/new"

echo "Seeding demo instance $SECRET (key '$KEY') on $API ..."

# Create the instance (auto-created on GET) and register the key.
curl -fsS "$API/api/instances/$SECRET" >/dev/null
curl -fsS -X POST "$API/api/instances/$SECRET/keys" \
  -H 'Content-Type: application/json' -d "{\"key\":\"$KEY\"}" >/dev/null || true

mkdir -p "$MAILDIR"

emit() { # emit <id> <from> <subject> <body>
  cat > "$MAILDIR/seed-$1.eml" <<EOF
From: $2
To: hello@$KEY.$DOMAIN
Subject: $3
Message-ID: <seed-$1@seed.local>
Date: $(date -R 2>/dev/null || date)
Content-Type: text/plain; charset=utf-8

$4
EOF
}

emit 1 "Welcome <welcome@acme.test>" "Welcome to Acme" "Thanks for signing up! Your code is 402913."
emit 2 "Security <noreply@acme.test>" "Your login code" "Use 771530 to finish signing in."
emit 3 "Newsletter <news@acme.test>" "This week at Acme" "Here is what shipped this week..."

echo "Dropped 3 sample emails into $MAILDIR"
echo
echo "Try it:"
echo "  Web UI:  open http://localhost:8081 and log in with secret: $SECRET"
echo "  API:     curl -s $API/api/instances/$SECRET/emails | jq '.items'"
echo
echo "(Emails appear within POLL_INTERVAL seconds.)"
