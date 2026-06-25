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
WEBROOT_HOST="$ROOT/certbot/www"
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

mkdir -p "$WEBROOT_HOST/.well-known/acme-challenge"

#region agent log
_ssl_log "H1" "ssl-renew.sh:start" "ssl-renew invoked" "{\"domain\":\"$DOMAIN\",\"certPath\":\"$CERT_PATH\"}"
#endregion

cert_readable() {
  [[ -r "$CERT_PATH" ]] || [[ -r "$LEGACY_CERT_PATH" ]]
}

cert_has_www_san() {
  local path="$1"
  openssl x509 -in "$path" -noout -text 2>/dev/null | grep -q "DNS:www.${DOMAIN}"
}

resolve_cert_path() {
  if [[ -r "$CERT_PATH" ]]; then
    echo "$CERT_PATH"
  elif [[ -r "$LEGACY_CERT_PATH" ]]; then
    echo "$LEGACY_CERT_PATH"
  fi
}

cert_status="missing"
cert_not_after=""
need_www_san=0
check_path="$(resolve_cert_path || true)"

if [[ -n "$check_path" ]]; then
  cert_not_after="$(openssl x509 -in "$check_path" -noout -enddate 2>/dev/null | cut -d= -f2- || true)"
  if openssl x509 -checkend 86400 -noout -in "$check_path" 2>/dev/null; then
    cert_status="valid"
  else
    cert_status="expired_or_expiring"
  fi
  if [[ "$check_path" == "$LEGACY_CERT_PATH" ]] || ! cert_has_www_san "$check_path"; then
    need_www_san=1
  fi
fi

#region agent log
_ssl_log "H2" "ssl-renew.sh:cert-check" "host cert state before renew" \
  "{\"status\":\"$cert_status\",\"notAfter\":\"$cert_not_after\",\"needWwwSan\":$need_www_san,\"checkPath\":\"$check_path\"}"
#endregion

#region agent log
preflight_probe="preflight-$(date +%s)"
echo ok > "$WEBROOT_HOST/.well-known/acme-challenge/$preflight_probe"
glc_acme="$(curl -sf -o /dev/null -w '%{http_code}' --max-time 8 -H "Host: $DOMAIN" "http://127.0.0.1/.well-known/acme-challenge/$preflight_probe" 2>/dev/null || echo '000')"
www_acme="$(curl -sf -o /dev/null -w '%{http_code}' --max-time 8 -H "Host: www.$DOMAIN" "http://127.0.0.1/.well-known/acme-challenge/$preflight_probe" 2>/dev/null || echo '000')"
rm -f "$WEBROOT_HOST/.well-known/acme-challenge/$preflight_probe"
glc_dns="$(dig +short A "$DOMAIN" @8.8.8.8 2>/dev/null | head -1 || true)"
www_dns="$(dig +short A "www.$DOMAIN" @8.8.8.8 2>/dev/null | head -1 || true)"
www_cname="$(dig +short CNAME "www.$DOMAIN" @8.8.8.8 2>/dev/null | head -1 || true)"
_ssl_log "H3" "ssl-renew.sh:acme-preflight" "webroot probe with temp file" \
  "{\"glcHttp\":\"$glc_acme\",\"wwwHttp\":\"$www_acme\",\"glcDns\":\"$glc_dns\",\"wwwDns\":\"$www_dns\",\"wwwCname\":\"$www_cname\"}"
#endregion

run_certbot() {
  $COMPOSE_SSL run --rm --no-deps --entrypoint certbot certbot "$@" 2>"$ROOT/.deploy-cache/certbot-last.err"
}

renew_rc=0
renew_mode="none"

if [[ "$cert_status" == "missing" ]]; then
  renew_mode="issue-glc-only"
  echo "No readable cert on host — issuing certificate for $DOMAIN only..."
  if ! run_certbot certonly \
    --webroot --webroot-path="$WEBROOT" \
    --email "$EMAIL" --agree-tos --no-eff-email \
    --cert-name "$DOMAIN" \
    -d "$DOMAIN"; then
    renew_rc=1
  fi
elif [[ "$cert_status" == "expired_or_expiring" ]] || [[ "${FORCE:-}" == "1" ]]; then
  renew_mode="force-glc-only"
  echo "Certificate expired or forced — renewing $DOMAIN..."
  if ! run_certbot certonly \
    --webroot --webroot-path="$WEBROOT" \
    --email "$EMAIL" --agree-tos --no-eff-email \
    --cert-name "$DOMAIN" --force-renewal \
    -d "$DOMAIN"; then
    renew_rc=1
  fi
elif [[ "$need_www_san" -eq 1 ]] && [[ "$www_acme" == "200" ]]; then
  renew_mode="expand-www"
  echo "Adding www.$DOMAIN to existing certificate (--expand)..."
  if ! run_certbot certonly \
    --webroot --webroot-path="$WEBROOT" \
    --email "$EMAIL" --agree-tos --no-eff-email \
    --cert-name "$DOMAIN" --expand \
    -d "$DOMAIN" -d "www.$DOMAIN"; then
    renew_rc=1
    #region agent log
    _ssl_log "H6" "ssl-renew.sh:expand-fail" "www expand failed; keeping glc.cool-only cert" "{}"
    #endregion
    echo "WARNING: Could not add www.$DOMAIN to certificate. Keeping valid $DOMAIN cert."
    echo "Use https://$DOMAIN (not www). Fix DNS/webroot for www, then redeploy."
    renew_rc=0
    renew_mode="expand-failed-keep-glc"
  fi
elif [[ "$need_www_san" -eq 1 ]]; then
  renew_mode="skip-www-webroot-bad"
  echo "WARNING: www webroot preflight returned HTTP $www_acme (expected 200). Skipping www SAN; keeping $DOMAIN cert."
  #region agent log
  _ssl_log "H6" "ssl-renew.sh:skip-www" "www webroot preflight failed" "{\"wwwHttp\":\"$www_acme\"}"
  #endregion
else
  renew_mode="quiet-renew"
  echo "Certificate valid — quiet renew..."
  if ! run_certbot renew --webroot --webroot-path="$WEBROOT" --quiet --non-interactive; then
    renew_rc=1
  fi
fi

certbot_err=""
if [[ -f "$ROOT/.deploy-cache/certbot-last.err" ]]; then
  certbot_err="$(tail -c 2000 "$ROOT/.deploy-cache/certbot-last.err" | tr '\n' ' ' | tr '"' "'")"
fi

#region agent log
_ssl_log "H4" "ssl-renew.sh:certbot" "certbot finished" \
  "{\"exitCode\":$renew_rc,\"mode\":\"$renew_mode\",\"stderrTail\":\"$certbot_err\"}"
#endregion

if [[ "$renew_rc" -ne 0 ]]; then
  echo "Certbot failed. Last output:"
  cat "$ROOT/.deploy-cache/certbot-last.err" 2>/dev/null || true
  exit 1
fi

check_path="$(resolve_cert_path || true)"
if [[ -z "$check_path" ]]; then
  #region agent log
  _ssl_log "H5" "ssl-renew.sh:fail" "no readable cert after renew" "{}"
  #endregion
  exit 1
fi

echo "Recreating nginx to pick up certificate..."
$COMPOSE up -d --no-build --force-recreate nginx

echo "Verifying nginx configuration..."
if ! $COMPOSE exec -T nginx nginx -t 2>"$ROOT/.deploy-cache/nginx-test.err"; then
  cat "$ROOT/.deploy-cache/nginx-test.err" 2>/dev/null || true
  #region agent log
  _ssl_log "H5" "ssl-renew.sh:fail" "nginx -t failed after recreate" "{}"
  #endregion
  exit 1
fi

new_not_after="$(openssl x509 -in "$check_path" -noout -enddate 2>/dev/null | cut -d= -f2- || true)"
new_fingerprint="$(openssl x509 -in "$check_path" -noout -fingerprint -sha256 2>/dev/null | cut -d= -f2- || true)"
has_www="$(cert_has_www_san "$check_path" && echo true || echo false)"
#region agent log
_ssl_log "H2" "ssl-renew.sh:cert-after" "host cert state after renew" \
  "{\"notAfter\":\"$new_not_after\",\"fingerprint\":\"$new_fingerprint\",\"hasWwwSan\":$has_www}"
#endregion

echo "Certificate dates (on disk):"
openssl x509 -in "$check_path" -noout -dates

if ! openssl x509 -checkend 86400 -noout -in "$check_path" 2>/dev/null; then
  #region agent log
  _ssl_log "H5" "ssl-renew.sh:fail" "cert still expires within 24h after renew" "{\"notAfter\":\"$new_not_after\"}"
  #endregion
  echo "ERROR: Certificate still invalid or expiring within 24 hours."
  exit 1
fi

served_fingerprint=""
for attempt in 1 2 3 4 5; do
  served_fingerprint="$(echo | openssl s_client -servername "$DOMAIN" -connect 127.0.0.1:443 2>/dev/null \
    | openssl x509 -noout -fingerprint -sha256 2>/dev/null | cut -d= -f2- || true)"
  if [[ -n "$served_fingerprint" ]]; then
    break
  fi
  sleep 2
done

#region agent log
_ssl_log "H5" "ssl-renew.sh:served-cert" "cert served by nginx on localhost" \
  "{\"fingerprint\":\"$served_fingerprint\",\"attempts\":\"$attempt\"}"
#endregion

if [[ -z "$served_fingerprint" ]]; then
  echo "WARNING: Could not verify cert via localhost:443. Disk cert is valid."
elif [[ "$served_fingerprint" != "$new_fingerprint" ]]; then
  #region agent log
  _ssl_log "H5" "ssl-renew.sh:fail" "nginx serving different cert than disk" \
    "{\"disk\":\"$new_fingerprint\",\"served\":\"$served_fingerprint\"}"
  #endregion
  echo "ERROR: Nginx is not serving the renewed certificate."
  exit 1
fi

#region agent log
_ssl_log "H1" "ssl-renew.sh:success" "ssl renew verified" "{\"notAfter\":\"$new_not_after\",\"hasWwwSan\":$has_www,\"mode\":\"$renew_mode\"}"
#endregion
echo "SSL renew OK — valid until $new_not_after (www on cert: $has_www)"
if [[ "$has_www" == "false" ]]; then
  echo "NOTE: Open https://$DOMAIN on phones — avoid https://www.$DOMAIN until www is on the cert."
fi
