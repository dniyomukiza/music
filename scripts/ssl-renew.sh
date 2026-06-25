#!/usr/bin/env bash
# Renew Let's Encrypt certs for glc.cool and reload nginx.
# Called automatically from scripts/deploy-production.sh on every deploy.
# Optional cron (belt-and-suspenders): 0 3,15 * * * .../scripts/ssl-renew.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="${COMPOSE:-docker compose --profile video}"
COMPOSE_SSL="${COMPOSE_SSL:-docker compose --profile video --profile ssl}"
WEBROOT="/var/www/certbot"
EMAIL="${SSL_CONTACT_EMAIL:-didyom1@gmail.com}"
CERT_PATH="/etc/letsencrypt/live/www.glc.cool/fullchain.pem"

mkdir -p certbot/www

renew_args=(renew --webroot --webroot-path="$WEBROOT" --non-interactive)
if [[ "${FORCE:-}" == "1" ]]; then
  renew_args+=(--force-renewal)
else
  renew_args+=(--quiet)
fi

# Auto force-renew if cert is missing, expired, or expires within 24 hours.
if [[ ! -f "$CERT_PATH" ]] \
   || ! openssl x509 -checkend 86400 -noout -in "$CERT_PATH" 2>/dev/null; then
  echo "Certificate missing or expiring within 24h — forcing renewal."
  renew_args=(renew --webroot --webroot-path="$WEBROOT" --force-renewal --non-interactive)
fi

if [[ ! -d /etc/letsencrypt/live/www.glc.cool ]]; then
  echo "No cert at /etc/letsencrypt/live/www.glc.cool — issuing first certificate..."
  $COMPOSE_SSL run --rm --no-deps --entrypoint certbot certbot certonly \
    --webroot --webroot-path="$WEBROOT" \
    --email "$EMAIL" --agree-tos --no-eff-email \
    -d www.glc.cool -d glc.cool
else
  $COMPOSE_SSL run --rm --no-deps --entrypoint certbot certbot "${renew_args[@]}"
fi

echo "Reloading nginx to load certificate..."
$COMPOSE exec -T nginx nginx -s reload

if [[ -f "$CERT_PATH" ]]; then
  echo "Certificate dates:"
  openssl x509 -in "$CERT_PATH" -noout -dates
else
  echo "Warning: certificate file still missing after renew."
  exit 1
fi
