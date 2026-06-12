#!/usr/bin/env bash
# Run E2E tests with a visible Chromium window (headed mode).
# Use for debugging flows while watching the browser. Headless CI/default: ./e2e/run_tests.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export E2E_TESTING="${E2E_TESTING:-1}"
export FLASK_ENV="${FLASK_ENV:-development}"
export E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:5000}"
export E2E_HEADED="${E2E_HEADED:-1}"

if ! HEALTH_JSON="$(curl -sf "${E2E_BASE_URL}/health" 2>/dev/null)"; then
  echo "ERROR: App not healthy at ${E2E_BASE_URL}/health"
  echo "Start the server first: E2E_TESTING=1 FLASK_ENV=development python run.py"
  exit 1
fi

if ! echo "${HEALTH_JSON}" | python -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('e2e_testing') else 1)" 2>/dev/null; then
  echo "ERROR: Flask at ${E2E_BASE_URL} is not running with E2E_TESTING=1."
  echo "Restart: E2E_TESTING=1 FLASK_ENV=development python run.py"
  exit 1
fi

pip install -q -r e2e/requirements-e2e.txt
playwright install chromium

mkdir -p e2e/test-results

PYTEST_ARGS=("$@")
if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
  # Fast slices by default — add paths or -m flags to widen scope
  PYTEST_ARGS=(-m "smoke or auth" "e2e/tests")
fi

echo "Browser mode: headed Chromium, slowmo=300ms, trace/video on failure"
echo "Artifacts: e2e/test-results/"
python -c "from e2e.config import get_config; c=get_config(); print('Stripe E2E:', 'enabled (STRIPE_SECRET_FOR_TEST)' if c.stripe_enabled else 'disabled — set STRIPE_SECRET_FOR_TEST=sk_test_... in .env')" 2>/dev/null || true
echo ""

pytest -c e2e/pytest.browser.ini "${PYTEST_ARGS[@]}"
