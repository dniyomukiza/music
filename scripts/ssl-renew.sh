#!/usr/bin/env bash
# Renew Let's Encrypt certs for glc.cool and reload nginx.
# Called automatically from scripts/deploy-production.sh on every deploy.
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="${COMPOSE:-docker compose --profile video}"
COMPOSE_SSL="${COMPOSE_SSL:-docker compose --profile video --profile ssl}"
WEBROOT="/var/www/certbot"
EMAIL="${SSL_CONTACT_EMAIL:-didyom1@gmail.com}"
DOMAIN="glc.cool"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
LEGACY_CERT_PATH="/etc/letsencrypt/live/www.glc.cool/fullchain.pem"
DEBUG_LOG="${SSL_DEBUG_LOG:-$ROOT/.cursor/debug-fe2ff6.log}"
RUN_ID="${SSL_RUN_ID:-pre-fix}"

#region agent log
_ssl_log() {
  local hypothesis_id="$1" location="$2" message="$3" data_json="${4:-{}}"
  mkdir -p "$(dirname "$DEBUG_LOG")" "$ROOT/.deploy-cache"
  local ts
  ts=$(python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || date +%s000)
  printf '{"sessionId":"fe2ff6","runId":"%s","hypothesisId":"%s","location":"%s","message":"%s","data":%s,"timestamp":%s}\n' \
    "$RUN_ID" "$hypothesis_id" "$location" "$message" "$data_json" "$ts" >> "$DEBUG_LOG"
  printf '{"sessionId":"fe2ff6","runId":"%s","hypothesisId":"%s","location":"%s","message":"%s","data":%s,"timestamp":%s}\n' \
    "$RUN_ID" "$hypothesis_id" "$location" "$message" "$data_json" "$ts" >> "$ROOT/.deploy-cache/ssl-renew-debug.ndjson"
}
#endregion

mkdir -p certbot/www

#region agent log
_ssl_log "H1" "ssl-renew.sh:start" "ssl-renew invoked" "{\"domain\":\"$DOMAIN\",\"certPath\":\"$CERT_PATH\",\"webroot\":\"$WEBROOT\"}"
#endregion

cert_status="missing"
cert_not_after=""
check_path="$CERT_PATH"
if [[ ! -f "$check_path" && -f "$LEGACY_CERT_PATH" ]]; then
  check_path="$LEGACY_CERT_PATH"
  cert_status="expired_or_expiring"
fi
if [[ -f "$check_path" ]]; then
  cert_not_after="$(openssl x509 -in "$check_path" -noout -enddate 2>/dev/null | cut -d= -f2- || true)"
  if [[ "$cert_status" != "expired_or_expiring" ]]; then
    if openssl x509 -checkend 0 -noout -in "$check_path" 2>/dev/null; then
      cert_status="valid"
    elif openssl x509 -checkend 86400 -noout -in "$check_path" 2>/dev/null; then
      cert_status="expiring_soon"
    else
      cert_status="expired_or_expiring"
    fi
  fi
  # Legacy www cert path: always re-issue under glc.cool only.
  if [[ "$check_path" == "$LEGACY_CERT_PATH" && ! -f "$CERT_PATH" ]]; then
    cert_status="expired_or_expiring"
  fi
fi

#region agent log
_ssl_log "H2" "ssl-renew.sh:cert-check" "host cert state before renew" \
  "{\"status\":\"$cert_status\",\"notAfter\":\"$cert_not_after\"}"
#endregion

#region agent log
acme_code="$(curl -sf -o /dev/null -w '%{http_code}' --max-time 8 -H 'Host: glc.cool' http://127.0.0.1/.well-known/acme-challenge/ssl-probe 2>/dev/null || echo '000')"
glc_dns="$(dig +short A glc.cool 2>/dev/null | head -1 || true)"
www_dns="$(dig +short A www.glc.cool 2>/dev/null | head -1 || true)"
_ssl_log "H3" "ssl-renew.sh:acme-probe" "HTTP acme webroot probe from host" "{\"httpStatus\":\"$acme_code\"}"
_ssl_log "H6" "ssl-renew.sh:dns" "DNS A records for cert domains" "{\"glcCool\":\"$glc_dns\",\"wwwGlcCool\":\"$www_dns\"}"
#endregion

certbot_domains=(-d "$DOMAIN")

renew_rc=0
if [[ "$cert_status" == "missing" ]]; then
  echo "No cert — issuing first certificate..."
  if ! $COMPOSE_SSL run --rm --no-deps --entrypoint certbot certbot certonly \
    --webroot --webroot-path="$WEBROOT" \
    --email "$EMAIL" --agree-tos --no-eff-email \
    "${certbot_domains[@]}" 2>"$ROOT/.deploy-cache/certbot-last.err"; then
    renew_rc=1
  fi
elif [[ "$cert_status" == "expired_or_expiring" ]] || [[ "${FORCE:-}" == "1" ]]; then
  echo "Certificate expired or expiring — certonly force-renewal..."
  if ! $COMPOSE_SSL run --rm --no-deps --entrypoint certbot certbot certonly \
    --webroot --webroot-path="$WEBROOT" \
    --email "$EMAIL" --agree-tos --no-eff-email \
    --force-renewal \
    "${certbot_domains[@]}" 2>"$ROOT/.deploy-cache/certbot-last.err"; then
    renew_rc=1
  fi
else
  echo "Certificate valid — quiet renew..."
  if ! $COMPOSE_SSL run --rm --no-deps --entrypoint certbot certbot renew \
    --webroot --webroot-path="$WEBROOT" --quiet --non-interactive 2>"$ROOT/.deploy-cache/certbot-last.err"; then
    renew_rc=1
  fi
fi

certbot_err=""
if [[ -f "$ROOT/.deploy-cache/certbot-last.err" ]]; then
  certbot_err="$(tail -c 2000 "$ROOT/.deploy-cache/certbot-last.err" | tr '\n' ' ' | tr '"' "'")"
fi

#region agent log
_ssl_log "H4" "ssl-renew.sh:certbot" "certbot finished" \
  "{\"exitCode\":$renew_rc,\"stderrTail\":\"$certbot_err\"}"
#endregion

if [[ "$renew_rc" -ne 0 ]]; then
  echo "Certbot failed. Last output:"
  cat "$ROOT/.deploy-cache/certbot-last.err" 2>/dev/null || true
  exit 1
fi

echo "Recreating nginx to pick up renewed certificate..."
$COMPOSE up -d --no-build --force-recreate nginx

echo "Reloading nginx..."
$COMPOSE exec -T nginx nginx -s reload

if [[ ! -f "$CERT_PATH" ]]; then
  #region agent log
  _ssl_log "H5" "ssl-renew.sh:fail" "cert file missing after renew" "{}"
  #endregion
  exit 1
fi

new_not_after="$(openssl x509 -in "$CERT_PATH" -noout -enddate 2>/dev/null | cut -d= -f2- || true)"
#region agent log
_ssl_log "H2" "ssl-renew.sh:cert-after" "host cert state after renew" "{\"notAfter\":\"$new_not_after\"}"
#endregion

#region agent log
served_not_after="$(echo | openssl s_client -servername glc.cool -connect 127.0.0.1:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2- || true)"
_ssl_log "H5" "ssl-renew.sh:served-cert" "cert served by nginx on localhost" "{\"notAfter\":\"$served_not_after\"}"
#endregion

echo "Certificate dates (on disk):"
openssl x509 -in "$CERT_PATH" -noout -dates

if ! openssl x509 -checkend 86400 -noout -in "$CERT_PATH" 2>/dev/null; then
  #region agent log
  _ssl_log "H5" "ssl-renew.sh:fail" "cert still expires within 24h after renew" "{\"notAfter\":\"$new_not_after\"}"
  #endregion
  echo "ERROR: Certificate still invalid or expiring within 24 hours."
  exit 1
fi

if [[ -n "$served_not_after" && "$served_not_after" != "$new_not_after" ]]; then
  #region agent log
  _ssl_log "H5" "ssl-renew.sh:fail" "nginx serving different cert than disk" \
    "{\"disk\":\"$new_not_after\",\"served\":\"$served_not_after\"}"
  #endregion
  echo "ERROR: Nginx is not serving the renewed certificate."
  exit 1
fi

#region agent log
_ssl_log "H1" "ssl-renew.sh:success" "ssl renew verified" "{\"notAfter\":\"$new_not_after\"}"
#endregion
echo "SSL renew OK — valid until $new_not_after"
