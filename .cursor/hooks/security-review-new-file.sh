#!/usr/bin/env bash
# Security review hook: runs after agent Write. Scans new/changed source for common issues.
# Aligned with .cursor/agents/security-auditor.md — deterministic checks, warnings to stderr.
set -euo pipefail

input=$(cat)

file_path=$(python3 - <<'PY' "$input"
import json, sys
raw = sys.argv[1]
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(0)
for key in ("file_path", "path", "filePath", "file"):
    val = data.get(key)
    if isinstance(val, str) and val.strip():
        print(val.strip())
        break
PY
)

[[ -n "${file_path:-}" ]] || exit 0
[[ -f "$file_path" ]] || exit 0

case "$file_path" in
  */node_modules/*|*/.venv/*|*/venv/*|*/__pycache__/*|*/.git/*|*/certbot/conf/*)
    exit 0
    ;;
esac

case "$file_path" in
  *.py|*.sh|*.bash|*.js|*.ts|*.tsx|*.jsx|*.html|*.jinja|*.jinja2|*.sql)
    ;;
  *)
    exit 0
    ;;
esac

is_new_file() {
  local f="$1"
  local st
  st=$(git status --porcelain -- "$f" 2>/dev/null | head -1 || true)
  [[ "$st" == \?\?* ]] && return 0
  [[ "$st" == A* ]] && return 0
  if ! git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    return 0
  fi
  if [[ -z "$(git log -1 --format=%H -- "$f" 2>/dev/null || true)" ]]; then
    return 0
  fi
  return 1
}

is_changed_file() {
  local f="$1"
  local st
  st=$(git status --porcelain -- "$f" 2>/dev/null | head -1 || true)
  [[ -n "$st" ]] && return 0
  return 1
}

# Run on new files OR any modified tracked/untracked source write
is_new_file "$file_path" || is_changed_file "$file_path" || exit 0

NEW=0
is_new_file "$file_path" && NEW=1

CRITICAL=""
HIGH=""
MEDIUM=""

filter_placeholders() {
  grep -viE 'user:password@|your-|example|placeholder|changeme|xxx|\.\.\.|\.env\.example' || true
}

# --- Critical: secrets / credentials ---
secret_hits=$(grep -nE \
  -e 'postgresql://[^[:space:]"'\''`]+@[^[:space:]"'\''`]+' \
  -e 'mysql://[^[:space:]"'\''`]+@[^[:space:]"'\''`]+' \
  -e 'mongodb(\+srv)?://[^[:space:]"'\''`]+@[^[:space:]"'\''`]+' \
  -e 'sk_live_[0-9a-zA-Z]{16,}' \
  -e 'sk_test_[0-9a-zA-Z]{16,}' \
  -e 'whsec_[0-9a-zA-Z]{16,}' \
  -e 'AKIA[0-9A-Z]{16}' \
  -e 'JWT_SECRET_KEY\s*=\s*["'\''`][^"'\''`\s]+["'\''`]' \
  -e '(password|passwd|secret|api_key|apikey)\s*=\s*["'\''`][^"'\''`\s]{8,}["'\''`]' \
  "$file_path" 2>/dev/null | filter_placeholders || true)
[[ -n "$secret_hits" ]] && CRITICAL+="Hardcoded secret/credential:\n${secret_hits}\n"

# --- High (full review on new files; secrets always) ---
if [[ "$NEW" -eq 1 ]]; then
  xss_hits=$(grep -nE '\|safe|innerHTML\s*=|dangerouslySetInnerHTML' "$file_path" 2>/dev/null || true)
  [[ -n "$xss_hits" ]] && HIGH+="Possible XSS (unsafe HTML/render):\n${xss_hits}\n"

  exec_hits=$(grep -nE '\beval\s*\(|\bexec\s*\(|pickle\.loads|shell\s*=\s*True' "$file_path" 2>/dev/null || true)
  [[ -n "$exec_hits" ]] && HIGH+="Dangerous execution pattern:\n${exec_hits}\n"

  sql_hits=$(grep -nE 'text\s*\(\s*f["'\''`]|\.execute\s*\(\s*f["'\''`]|f["'\''`].*(SELECT|INSERT|UPDATE|DELETE|DROP)\s' "$file_path" 2>/dev/null || true)
  [[ -n "$sql_hits" ]] && HIGH+="Possible SQL injection (dynamic SQL):\n${sql_hits}\n"

  route_hits=$(grep -nE '@(bp|book_bp|.*_bp)\.route' "$file_path" 2>/dev/null | grep -v 'login_required' || true)
  if [[ -n "$route_hits" ]] && grep -qE '@(bp|book_bp|.*_bp)\.route' "$file_path" 2>/dev/null; then
    if ! grep -q 'login_required\|@admin' "$file_path" 2>/dev/null; then
      MEDIUM+="New route file without obvious auth decorator — verify access control.\n"
    fi
  fi
fi

[[ -z "$CRITICAL$HIGH$MEDIUM" ]] && exit 0

label="security-review"
[[ "$NEW" -eq 1 ]] && label="security-review (new file)" || label="security-review (changed file)"

echo "⚠️  [hook:${label}] ${file_path}" >&2
[[ -n "$CRITICAL" ]] && { echo "  CRITICAL (fix before commit/deploy):" >&2; echo -e "$CRITICAL" | head -25 >&2; }
[[ -n "$HIGH" ]] && { echo "  HIGH:" >&2; echo -e "$HIGH" | head -25 >&2; }
[[ -n "$MEDIUM" ]] && { echo "  MEDIUM:" >&2; echo -e "$MEDIUM" | head -10 >&2; }
echo "  → Run security-auditor for full review. Use env vars; see .env.example." >&2
exit 0
