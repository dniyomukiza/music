#!/usr/bin/env bash
# Free Docker disk before compose build while preserving recent BuildKit cache.
# Safe defaults:
#   - docker container prune (stopped containers only)
#   - docker image prune (dangling <none> layers from failed builds)
#   - docker builder prune with age/size cap (NOT --all)
# Does NOT run: docker system prune -a, docker build --no-cache
set -euo pipefail

DEBUG_LOG="${DEBUG_LOG_PATH:-.deploy-cache/docker-prebuild-debug.ndjson}"
MIN_FREE_MB="${DOCKER_MIN_FREE_MB:-2048}"
KEEP_BUILD_CACHE="${DOCKER_KEEP_BUILD_CACHE:-5GB}"
BUILD_CACHE_MAX_AGE="${DOCKER_PRUNE_BUILD_CACHE_OLDER_THAN:-96h}"
UNUSED_IMAGE_MAX_AGE="${DOCKER_PRUNE_UNUSED_IMAGES_OLDER_THAN:-48h}"

mkdir -p "$(dirname "$DEBUG_LOG")"

# #region agent log
_debug_log() {
  local hypothesis_id="$1"
  local message="$2"
  local data_json="$3"
  local ts
  ts="$(python3 -c 'import time; print(int(time.time() * 1000))' 2>/dev/null || date +%s000)"
  printf '%s\n' \
    "{\"sessionId\":\"fe2ff6\",\"hypothesisId\":\"${hypothesis_id}\",\"location\":\"docker-prebuild-cleanup.sh\",\"message\":\"${message}\",\"data\":${data_json},\"timestamp\":${ts}}" \
    >>"$DEBUG_LOG" 2>/dev/null || true
}
# #endregion

# #region agent log
_disk_snapshot() {
  local label="$1"
  local free_mb reclaimable
  free_mb="$(df -m / 2>/dev/null | awk 'NR==2 {print $4}' || echo 0)"
  reclaimable="$(docker system df 2>/dev/null | awk 'NR>1 {gsub(/[^0-9.]/,"",$4); sum+=$4} END {printf "%.0f", sum+0}' || echo 0)"
  _debug_log "SNAP" "${label}" "{\"free_mb_root\":${free_mb},\"docker_reclaimable_mb_approx\":${reclaimable}}"
  echo "--- [${label}] root free: ${free_mb} MB; docker reclaimable ~${reclaimable} MB ---"
  docker system df 2>/dev/null || true
}
# #endregion

echo "=== Docker pre-build cleanup (preserving recent build cache) ==="
# #region agent log
_disk_snapshot "before_cleanup"
# #endregion

# Hypothesis A: dangling images from failed/partial builds fill disk
DANGLING_OUT=""
DANGLING_OUT="$(docker image prune -f 2>&1 || true)"
# #region agent log
_debug_log "A" "dangling_image_prune" "{\"lines\":$(printf '%s' "$DANGLING_OUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().splitlines()[-3:]))' 2>/dev/null || echo '[]')}"
# #endregion
echo "$DANGLING_OUT" | tail -3 || true

# Hypothesis C: stopped containers retain writable layers
CONTAINER_OUT=""
CONTAINER_OUT="$(docker container prune -f 2>&1 || true)"
# #region agent log
_debug_log "C" "container_prune" "{\"lines\":$(printf '%s' "$CONTAINER_OUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().splitlines()[-2:]))' 2>/dev/null || echo '[]')}"
# #endregion
echo "$CONTAINER_OUT" | tail -2 || true

# Hypothesis B: unbounded BuildKit cache fills containerd ingest store
BUILDER_OUT=""
if docker builder prune --help 2>&1 | grep -q 'keep-storage'; then
  BUILDER_OUT="$(docker builder prune -f --keep-storage "$KEEP_BUILD_CACHE" 2>&1 || true)"
else
  BUILDER_OUT="$(docker builder prune -f --filter "until=${BUILD_CACHE_MAX_AGE}" 2>&1 || true)"
fi
# #region agent log
_debug_log "B" "builder_prune_capped" "{\"keep_storage\":\"${KEEP_BUILD_CACHE}\",\"lines\":$(printf '%s' "$BUILDER_OUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().splitlines()[-3:]))' 2>/dev/null || echo '[]')}"
# #endregion
echo "$BUILDER_OUT" | tail -3 || true

# Hypothesis D: old unused tagged images remain after superseded rebuilds
FREE_MB="$(df -m / 2>/dev/null | awk 'NR==2 {print $4}' || echo 99999)"
if [ "${FREE_MB}" -lt "${MIN_FREE_MB}" ]; then
  echo "--- Low disk (${FREE_MB} MB free < ${MIN_FREE_MB} MB): pruning unused images older than ${UNUSED_IMAGE_MAX_AGE} ---"
  OLD_IMG_OUT=""
  OLD_IMG_OUT="$(docker image prune -a -f --filter "until=${UNUSED_IMAGE_MAX_AGE}" 2>&1 || true)"
  # #region agent log
  _debug_log "D" "low_disk_unused_image_prune" "{\"free_mb_before\":${FREE_MB},\"lines\":$(printf '%s' "$OLD_IMG_OUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().splitlines()[-2:]))' 2>/dev/null || echo '[]')}"
  # #endregion
  echo "$OLD_IMG_OUT" | tail -2 || true
  if docker builder prune --help 2>&1 | grep -q 'keep-storage'; then
    docker builder prune -f --keep-storage "3GB" 2>/dev/null || true
  fi
fi

# Hypothesis E: deploy previously skipped cleanup unless FORCE_REBUILD=1
# #region agent log
_debug_log "E" "prebuild_cleanup_ran" "{\"min_free_mb\":${MIN_FREE_MB},\"keep_build_cache\":\"${KEEP_BUILD_CACHE}\"}"
# #endregion

# #region agent log
_disk_snapshot "after_cleanup"
# #endregion
echo "=== Pre-build cleanup finished (BuildKit cache capped, not wiped) ==="
