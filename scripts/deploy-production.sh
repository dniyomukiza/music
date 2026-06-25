#!/usr/bin/env bash
# Production deploy on the VM (called from .github/workflows/deploy.yml after git pull).
# Fast path (~2–5 min): pull, up --no-build, restart app/fastapi (code is bind-mounted).
# Full pip/apt rebuild only for services whose Dockerfile/requirements actually changed.
set -euo pipefail

cd /home/didyom1/music
DEPLOY_START=$(date +%s)

CACHE_DIR=".deploy-cache"
mkdir -p "$CACHE_DIR"

# Track last known good commit so rollback can restore it.
LAST_GOOD_COMMIT_FILE="$CACHE_DIR/last_good_commit"

COMPOSE=(docker compose --profile video)
COMPOSE_UP=("${COMPOSE[@]}" up -d)

hash_file() { sha256sum "$1" | awk '{print $1}'; }
cache_key() { echo "$1" | tr '/' '_'; }

# Return 0 if tracked file changed since last successful deploy (or cache missing after init).
file_changed() {
  local f="$1"
  [ -f "$f" ] || return 1
  local key h old
  key="$(cache_key "$f")"
  h="$(hash_file "$f")"
  old="$(cat "$CACHE_DIR/$key.hash" 2>/dev/null || true)"
  if [ -z "$old" ]; then
    [ -f "$CACHE_DIR/.initialized" ] && return 0
    return 1
  fi
  [ "$h" != "$old" ]
}

save_hash() {
  local f="$1"
  [ -f "$f" ] || return 0
  hash_file "$f" > "$CACHE_DIR/$(cache_key "$f").hash"
}

save_all_hashes() {
  local f
  for f in requirements.txt requirements-fastapi.txt Dockerfile Dockerfile.nginx Dockerfile.uvi docker-compose.yml nginx.conf; do
    save_hash "$f"
  done
  touch "$CACHE_DIR/.initialized"
}

service_built_image_id() {
  local svc="$1"
  local id=""
  id="$("${COMPOSE[@]}" images -q "$svc" 2>/dev/null | head -1 || true)"
  if [ -n "$id" ] && docker image inspect "$id" >/dev/null 2>&1; then
    echo "$id"
    return 0
  fi
  id="$(docker image ls -q --filter "label=com.docker.compose.service=${svc}" 2>/dev/null | head -1 || true)"
  if [ -n "$id" ] && docker image inspect "$id" >/dev/null 2>&1; then
    echo "$id"
    return 0
  fi
  return 1
}

echo "--- Pulling latest code ---"
git fetch origin
git reset --hard origin/enhancements
echo "Deploying commit: $(git log -1 --oneline)"

echo "--- Udev cleanup (errors ignored) ---"
sudo find /run/udev/data -type f -delete 2>/dev/null || true
sudo systemctl start systemd-udevd 2>/dev/null || true

BUILD_SERVICES=()
REBUILD_REASON=""

if [ "${FORCE_REBUILD:-0}" = "1" ]; then
  BUILD_SERVICES=(app fastapi nginx)
  REBUILD_REASON="FORCE_REBUILD=1"
elif ! docker image inspect myapp:latest >/dev/null 2>&1; then
  BUILD_SERVICES=(app)
  REBUILD_REASON="myapp:latest missing (app only)"
else
  if file_changed requirements.txt || file_changed Dockerfile; then
    BUILD_SERVICES+=(app)
    REBUILD_REASON="${REBUILD_REASON:+$REBUILD_REASON, }app deps/Dockerfile"
  fi
  if file_changed requirements-fastapi.txt || file_changed Dockerfile.uvi; then
    BUILD_SERVICES+=(fastapi)
    REBUILD_REASON="${REBUILD_REASON:+$REBUILD_REASON, }fastapi deps/Dockerfile"
  fi
  if file_changed Dockerfile.nginx; then
    BUILD_SERVICES+=(nginx)
    REBUILD_REASON="${REBUILD_REASON:+$REBUILD_REASON, }nginx Dockerfile"
  fi
  if ! service_built_image_id fastapi >/dev/null; then
    BUILD_SERVICES+=(fastapi)
    REBUILD_REASON="${REBUILD_REASON:+$REBUILD_REASON, }fastapi image missing"
  fi
  if ! service_built_image_id nginx >/dev/null; then
    BUILD_SERVICES+=(nginx)
    REBUILD_REASON="${REBUILD_REASON:+$REBUILD_REASON, }nginx image missing"
  fi
fi

# Deduplicate service names
if [ "${#BUILD_SERVICES[@]}" -gt 0 ]; then
  readarray -t BUILD_SERVICES < <(printf '%s\n' "${BUILD_SERVICES[@]}" | awk '!seen[$0]++')
fi

FAST_DEPLOY=0
if [ "${#BUILD_SERVICES[@]}" -eq 0 ]; then
  FAST_DEPLOY=1
  echo "--- Fast deploy (no image rebuild; code loads from bind mounts) ---"
  "${COMPOSE_UP[@]}" --no-build
  echo "--- Restarting app workers ---"
  "${COMPOSE[@]}" restart app fastapi || true
  "${COMPOSE[@]}" restart liquidsoap liquidsoap_video 2>/dev/null || true
else
  echo "--- Building Docker images: ${BUILD_SERVICES[*]} (${REBUILD_REASON}) ---"
  echo "--- Tip: routine code-only pushes should show 'Fast deploy' above ---"
  if [ -f scripts/docker-prebuild-cleanup.sh ]; then
    echo "--- Pre-build Docker cleanup (free disk; keep recent build cache) ---"
    chmod +x scripts/docker-prebuild-cleanup.sh 2>/dev/null || true
    DEBUG_LOG_PATH="$CACHE_DIR/docker-prebuild-debug.ndjson" \
      bash scripts/docker-prebuild-cleanup.sh || true
  fi
  BUILD_FLAGS=()
  if [ "${FORCE_REBUILD:-0}" = "1" ]; then
    BUILD_FLAGS+=(--pull)
  fi
  if ! "${COMPOSE[@]}" build "${BUILD_FLAGS[@]}" "${BUILD_SERVICES[@]}"; then
    echo "--- Build failed; keeping site up with existing images (fast fallback) ---"
    FAST_DEPLOY=1
    "${COMPOSE_UP[@]}" --no-build
    "${COMPOSE[@]}" restart app fastapi || true
    "${COMPOSE[@]}" restart liquidsoap liquidsoap_video 2>/dev/null || true
  else
    save_all_hashes
    "${COMPOSE_UP[@]}"
    echo "--- Post-build: remove dangling layers from superseded images ---"
    docker image prune -f >/dev/null 2>&1 || true
  fi
fi

if file_changed nginx.conf; then
  echo "--- nginx.conf changed; reloading nginx ---"
  if "${COMPOSE[@]}" ps nginx --status running -q 2>/dev/null | grep -q .; then
    "${COMPOSE[@]}" exec -T nginx nginx -t
    "${COMPOSE[@]}" exec -T nginx nginx -s reload
  else
    "${COMPOSE[@]}" up -d --no-build nginx
  fi
  save_hash nginx.conf
fi

if file_changed docker-compose.yml; then
  echo "--- docker-compose.yml changed; recreating nginx (cert/webroot volumes) ---"
  "${COMPOSE[@]}" up -d --no-build nginx
  save_hash docker-compose.yml
fi

echo "--- SSL certificate (Let's Encrypt auto-renew) ---"
chmod +x scripts/ssl-renew.sh 2>/dev/null || true
mkdir -p .deploy-cache
COMPOSE="docker compose --profile video" \
COMPOSE_SSL="docker compose --profile video --profile ssl" \
bash scripts/ssl-renew.sh

if [ "$FAST_DEPLOY" = 1 ]; then
  save_all_hashes
fi

docker image inspect myapp:latest --format 'myapp:latest OK' >/dev/null

# Fast deploy: app was only restarted — short health wait. Full build: longer (app start_period up to 6m).
if [ "$FAST_DEPLOY" = 1 ]; then
  HEALTH_TRIES=18
  HEALTH_SLEEP=5
else
  HEALTH_TRIES=36
  HEALTH_SLEEP=10
fi

echo "--- Waiting for app /health (tries=${HEALTH_TRIES}, sleep=${HEALTH_SLEEP}s) ---"
for i in $(seq 1 "$HEALTH_TRIES"); do
  if curl -sf --max-time 8 http://localhost:5000/health >/dev/null; then
    echo "App is up (${i}/${HEALTH_TRIES})."
    break
  fi
  echo "app health... ($i/${HEALTH_TRIES})"
  sleep "$HEALTH_SLEEP"
done

for i in $(seq 1 8); do
  if curl -sf --max-time 8 http://localhost/health >/dev/null 2>&1 \
    || curl -skf --max-time 8 https://localhost/health >/dev/null 2>&1; then
    echo "Nginx -> app OK."
    break
  fi
  echo "nginx->app... ($i/8)"
  sleep 5
done

for i in $(seq 1 8); do
  if curl -sf --max-time 8 http://localhost:8002/health >/dev/null; then
    echo "FastAPI OK."
    break
  fi
  echo "FastAPI... ($i/8)"
  sleep 5
done

ELAPSED=$(( $(date +%s) - DEPLOY_START ))
echo "Deploy finished in ${ELAPSED}s ($(( ELAPSED / 60 ))m $(( ELAPSED % 60 ))s). Mode: $([ "$FAST_DEPLOY" = 1 ] && echo FAST || echo BUILD:${BUILD_SERVICES[*]})."

# Mark last known good only when core health checks pass (rollback target stays reliable).
APP_OK=0
curl -sf --max-time 8 http://localhost:5000/health >/dev/null && APP_OK=1
if [ "$APP_OK" = 1 ]; then
  git rev-parse HEAD > "$LAST_GOOD_COMMIT_FILE"
  echo "Recorded last known good commit: $(cat "$LAST_GOOD_COMMIT_FILE")"
else
  echo "--- Warning: app /health not OK; last_good_commit not updated (rollback unchanged) ---"
fi
