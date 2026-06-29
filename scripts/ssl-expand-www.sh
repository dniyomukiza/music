#!/usr/bin/env bash
# One-time: add www.glc.cool to the Let's Encrypt cert (non-interactive).
# Run on the VM after DNS for www points to this server (CNAME or A record).
#
#   cd /home/didyom1/music && ./scripts/ssl-expand-www.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="${COMPOSE:-docker compose --profile video}"
COMPOSE_SSL="${COMPOSE_SSL:-docker compose --profile video --profile ssl}"
DOMAIN="${SSL_DOMAIN:-ndotonic.com}"
WEBROOT="/var/www/certbot"
WEBROOT_HOST="$ROOT/certbot/www"
EMAIL="${SSL_CONTACT_EMAIL:-didyom1@gmail.com}"

mkdir -p "$WEBROOT_HOST/.well-known/acme-challenge"
probe="expand-probe-$(date +%s)"
echo ok > "$WEBROOT_HOST/.well-known/acme-challenge/$probe"

echo "Checking webroot (expect HTTP 200 for both hosts)..."
for host in "$DOMAIN" "www.$DOMAIN"; do
  code="$(curl -sf -o /dev/null -w '%{http_code}' --max-time 8 -H "Host: $host" \
    "http://127.0.0.1/.well-known/acme-challenge/$probe" 2>/dev/null || echo '000')"
  echo "  $host → HTTP $code"
  if [[ "$code" != "200" ]]; then
    echo "ERROR: ACME webroot not reachable for $host. Fix nginx/certbot/www volumes first."
    rm -f "$WEBROOT_HOST/.well-known/acme-challenge/$probe"
    exit 1
  fi
done
rm -f "$WEBROOT_HOST/.well-known/acme-challenge/$probe"

echo "Expanding certificate to include www.$DOMAIN ..."
run_certbot() {
  $COMPOSE_SSL run --rm --no-deps -T \
    -e CERTBOT_NONINTERACTIVE=1 \
    --entrypoint certbot certbot "$@" \
    2>"$ROOT/.deploy-cache/certbot-last.err"
}
run_certbot certonly \
  --non-interactive --expand \
  --webroot --webroot-path="$WEBROOT" \
  --email "$EMAIL" --agree-tos --no-eff-email \
  --cert-name "$DOMAIN" \
  -d "$DOMAIN" -d "www.$DOMAIN"

echo "Reloading nginx..."
$COMPOSE exec -T nginx nginx -t
$COMPOSE exec -T nginx nginx -s reload || true

CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
openssl x509 -in "$CERT" -noout -dates
openssl x509 -in "$CERT" -noout -text | grep -A1 "Subject Alternative Name"

echo "Done. Test on phone: https://$DOMAIN and https://www.$DOMAIN"
