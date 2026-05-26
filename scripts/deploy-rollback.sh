#!/usr/bin/env bash
# Roll back to the last known good commit and restart services without rebuilding images.
set -euo pipefail

cd /home/didyom1/music

CACHE_DIR=".deploy-cache"
LAST_GOOD_COMMIT_FILE="$CACHE_DIR/last_good_commit"

if [ ! -f "$LAST_GOOD_COMMIT_FILE" ]; then
  echo "No last_good_commit file found at $LAST_GOOD_COMMIT_FILE; cannot automatically roll back."
  exit 1
fi

LAST_GOOD_COMMIT="$(cat "$LAST_GOOD_COMMIT_FILE")"

if [ -z "$LAST_GOOD_COMMIT" ]; then
  echo "last_good_commit file is empty; cannot automatically roll back."
  exit 1
fi

echo "--- Rolling back to last known good commit ---"
echo "Commit: $LAST_GOOD_COMMIT"

git fetch origin || true
git reset --hard "$LAST_GOOD_COMMIT"

COMPOSE=(docker compose --profile video)
COMPOSE_UP=("${COMPOSE[@]}" up -d)

echo "--- Bringing services up with last known good code (no rebuild) ---"
"${COMPOSE_UP[@]}" --no-build

echo "--- Restarting app workers after rollback ---"
"${COMPOSE[@]}" restart app fastapi || true
"${COMPOSE[@]}" restart liquidsoap liquidsoap_video 2>/dev/null || true

echo "--- Verifying health after rollback ---"
for i in $(seq 1 18); do
  if curl -sf --max-time 8 http://localhost:5000/health >/dev/null; then
    echo "App is up after rollback (${i}/18)."
    break
  fi
  echo "app health after rollback... ($i/18)"
  sleep 5
done

for i in $(seq 1 8); do
  if curl -sf --max-time 8 http://localhost/health >/dev/null 2>&1 \
    || curl -skf --max-time 8 https://localhost/health >/dev/null 2>&1; then
    echo "Nginx -> app OK after rollback."
    break
  fi
  echo "nginx->app after rollback... ($i/8)"
  sleep 5
done

for i in $(seq 1 8); do
  if curl -sf --max-time 8 http://localhost:8002/health >/dev/null; then
    echo "FastAPI OK after rollback."
    break
  fi
  echo "FastAPI after rollback... ($i/8)"
  sleep 5
done

echo "Rollback completed."

