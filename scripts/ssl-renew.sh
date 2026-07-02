#!/usr/bin/env bash
# Verify SSL on deploy; run certbot ONLY when renewal is actually needed.
# Never prompts (non-interactive + docker -T). Skips entirely when cert is valid 30+ days.
#
# Manual force-renew: FORCE=1 ./scripts/ssl-renew.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE="${COMPOSE:-docker compose --profile video}"
COMPOSE_SSL="${COMPOSE_SSL:-docker compose --profile video --profile ssl}"
WEBROOT="/var/www/certbot"
WEBROOT_HOST="$ROOT/certbot/www"
EMAIL="${SSL_CONTACT_EMAIL:-didyom1@gmail.com}"
# Canonical domain. `certbot renew` (renew-only mode) still renews ALL certs found
# under /etc/letsencrypt/renewal, so the legacy glc.cool cert keeps renewing too.
DOMAIN="${SSL_DOMAIN:-ndotonic.com}"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
RENEWAL_CONF="/etc/letsencrypt/renewal/${DOMAIN}.conf"
DEBUG_LOG="${SSL_DEBUG_LOG:-$ROOT/.cursor/debug-fe2ff6.log}"
RUN_ID="${SSL_RUN_ID:-deploy}"

mkdir -p "$WEBROOT_HOST/.well-known/acme-challenge" "$ROOT/.deploy-cache"

#region agent log
_ssl_log() {
  case "${DEBUG_AGENT_LOG:-}" in
    1|true|TRUE|yes|YES|on|ON) ;;
    *) return 0 ;;
  esac
  local hypothesis_id="$1" message="$2" data_json="${3:-{}}"
  local ts
  ts=$(python3 -c 'import time; print(int(time.time()*1000))' 2>/dev/null || date +%s000)
  printf '{"sessionId":"fe2ff6","runId":"%s","hypothesisId":"%s","location":"ssl-renew.sh","message":"%s","data":%s,"timestamp":%s}\n' \
    "$RUN_ID" "$hypothesis_id" "$message" "$data_json" "$ts" >> "$DEBUG_LOG"
}
#endregion

cert_exists() {
  if $COMPOSE exec -T nginx test -r "$CERT_PATH" 2>/dev/null; then
    return 0
  fi
  if [[ -r "$CERT_PATH" ]]; then
    return 0
  fi
  if [[ -f "$RENEWAL_CONF" ]]; then
    return 0
  fi
  return 1
}

# nginx:alpine has no openssl; use the certbot image (same /etc/letsencrypt mount).
cert_openssl() {
  $COMPOSE_SSL run --rm --no-deps -T --entrypoint openssl certbot "$@" 2>/dev/null
}

cert_checkend_seconds() {
  local seconds="$1"
  cert_exists || return 1
  if [[ -r "$CERT_PATH" ]] && command -v openssl >/dev/null 2>&1; then
    openssl x509 -in "$CERT_PATH" -noout -checkend "$seconds"
    return
  fi
  cert_openssl x509 -in "$CERT_PATH" -noout -checkend "$seconds"
}

cert_not_after() {
  cert_exists || return 0
  if [[ -r "$CERT_PATH" ]] && command -v openssl >/dev/null 2>&1; then
    openssl x509 -in "$CERT_PATH" -noout -enddate 2>/dev/null | cut -d= -f2- || true
    return
  fi
  cert_openssl x509 -in "$CERT_PATH" -noout -enddate 2>/dev/null | cut -d= -f2- || true
}

#region agent log
host_readable=$([[ -r "$CERT_PATH" ]] && echo true || echo false)
renewal_conf=$([[ -f "$RENEWAL_CONF" ]] && echo true || echo false)
nginx_readable=$($COMPOSE exec -T nginx test -r "$CERT_PATH" 2>/dev/null && echo true || echo false)
_ssl_log "H1" "cert visibility before decision" \
  "{\"hostReadable\":$host_readable,\"renewalConf\":$renewal_conf,\"nginxReadable\":$nginx_readable}"
#endregion

not_after="$(cert_not_after || true)"
if [[ -n "$not_after" ]]; then
  echo "Current certificate valid until: $not_after"
fi

# --- Skip certbot entirely when cert is good (fixes EOFError from spurious certonly runs) ---
if [[ "${FORCE:-}" != "1" ]] && cert_checkend_seconds 2592000; then
  echo "Certificate valid for 30+ days — skipping certbot (no container run)."
  #region agent log
  _ssl_log "H2" "skip certbot" "{\"mode\":\"skip-valid\",\"notAfter\":\"$not_after\"}"
  #endregion
  echo "SSL OK — $DOMAIN valid until $not_after (mode: skip-valid)"
  exit 0
fi

run_certbot() {
  # -T = no TTY (prevents interactive prompts → EOFError in CI)
  $COMPOSE_SSL run --rm --no-deps -T \
    -e CERTBOT_NONINTERACTIVE=1 \
    --entrypoint certbot certbot "$@" \
    2>"$ROOT/.deploy-cache/certbot-last.err"
}

renew_rc=0
renew_mode="none"

if [[ "${FORCE:-}" == "1" ]] || ! cert_checkend_seconds 86400; then
  renew_mode="force-renew"
  echo "Certificate expired, expiring within 24h, or FORCE=1 — force renewing..."
  if ! run_certbot certonly \
    --non-interactive \
    --webroot --webroot-path="$WEBROOT" \
    --email "$EMAIL" --agree-tos --no-eff-email \
    --cert-name "$DOMAIN" --force-renewal \
    -d "$DOMAIN" -d "www.$DOMAIN"; then
    renew_rc=1
  fi
elif cert_exists; then
  renew_mode="renew-only"
  echo "Running certbot renew (non-interactive; no certonly — avoids duplicate-cert prompt)..."
  if ! run_certbot renew \
    --non-interactive \
    --webroot --webroot-path="$WEBROOT" \
    --quiet; then
    renew_rc=1
  fi
else
  renew_mode="issue-new"
  echo "No certificate found — issuing new cert for $DOMAIN..."
  if ! run_certbot certonly \
    --non-interactive \
    --webroot --webroot-path="$WEBROOT" \
    --email "$EMAIL" --agree-tos --no-eff-email \
    --cert-name "$DOMAIN" \
    -d "$DOMAIN" -d "www.$DOMAIN"; then
    renew_rc=1
  fi
fi

#region agent log
err_tail=""
[[ -f "$ROOT/.deploy-cache/certbot-last.err" ]] && err_tail=$(tail -c 1500 "$ROOT/.deploy-cache/certbot-last.err" | tr '\n' ' ' | tr '"' "'")
_ssl_log "H3" "certbot finished" "{\"mode\":\"$renew_mode\",\"exitCode\":$renew_rc,\"stderrTail\":\"$err_tail\"}"
#endregion

if [[ "$renew_rc" -ne 0 ]]; then
  # If cert still valid on nginx, do not fail deploy (certbot noise only)
  if cert_checkend_seconds 86400; then
    echo "WARNING: certbot failed but existing certificate is still valid — continuing deploy."
    #region agent log
    _ssl_log "H4" "certbot failed but cert still valid" "{\"mode\":\"$renew_mode\"}"
    #endregion
    not_after="$(cert_not_after || true)"
    echo "SSL OK — $DOMAIN valid until $not_after (mode: $renew_mode, certbot-skipped-failure)"
    exit 0
  fi
  echo "Certbot failed. Last output:"
  cat "$ROOT/.deploy-cache/certbot-last.err" 2>/dev/null || true
  exit 1
fi

if cert_checkend_seconds 86400; then
  not_after="$(cert_not_after || true)"
  #region agent log
  _ssl_log "H2" "ssl success" "{\"mode\":\"$renew_mode\",\"notAfter\":\"$not_after\"}"
  #endregion
  echo "SSL OK — $DOMAIN valid until $not_after (mode: $renew_mode)"
  exit 0
fi

# certbot succeeded but expiry check failed — still OK if the cert file is present
if [[ "$renew_rc" -eq 0 ]] && cert_exists; then
  not_after="$(cert_not_after || true)"
  echo "SSL OK — $DOMAIN certificate present (mode: $renew_mode${not_after:+, valid until $not_after})"
  exit 0
fi

echo "ERROR: No valid certificate after renew."
exit 1
