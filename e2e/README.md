# Ink Studio E2E Tests (Playwright + pytest)

End-to-end tests for author and buyer workflows on the book platform (`/mybook`).

**Full framework design:** [`docs/TESTING.md`](../docs/TESTING.md)

## Prerequisites

1. **Running Flask app** with database configured (same `.env` as local dev).
2. **Environment variables:**

| Variable | Required | Purpose |
|----------|----------|---------|
| `E2E_TESTING=1` | Yes | Skips registration reCAPTCHA |
| `FLASK_ENV=development` | Recommended | Dev cookies, upload reCAPTCHA skip |
| `E2E_BASE_URL` | Optional | Test target URL (default `http://localhost:5000`). **Not** `FRONTEND_BASE_URL`. |
| `STRIPE_SECRET_FOR_TEST` | For `@stripe` tests | `sk_test_...` in `.env`; production `STRIPE_SECRET_KEY` unchanged |
| `FRONTEND_BASE_URL` | For Stripe redirects in the app | Must match checkout return URLs when running Stripe tests |
| `STRIPE_CONNECT_ALLOW_PLATFORM_ONLY=1` | Recommended | Authors can list without Connect onboarding |

## Install

```bash
pip install -r requirements.txt -r e2e/requirements-e2e.txt
playwright install chromium
```

## Start the app

```bash
E2E_TESTING=1 FLASK_ENV=development python run.py
```

## Run tests

```bash
# Quick default (no Stripe) — sets E2E_BASE_URL=http://localhost:5000
./e2e/run_tests.sh

# Specific markers
pytest -c e2e/pytest.ini e2e/tests -m author
pytest -c e2e/pytest.ini e2e/tests -m buyer
pytest -c e2e/pytest.ini e2e/tests -m stripe

# Parallel full workflows
pytest -c e2e/pytest.ini e2e/tests -m full_workflow -n 2

# Headless (default) — runs in background
./e2e/run_tests.sh

# Visible browser — watch tests run (smoke + auth by default)
./e2e/run_tests_browser.sh

# Browser: single file or marker
./e2e/run_tests_browser.sh e2e/tests/test_auth.py -v
./e2e/run_tests_browser.sh -m author e2e/tests

# Browser: Playwright Inspector (step through actions)
PWDEBUG=1 ./e2e/run_tests_browser.sh e2e/tests/test_login_buyer.py -v

# Cursor / VS Code: Run and Debug → "E2E: Current test file (browser)"
# Start Flask first with "Flask (E2E)" or: E2E_TESTING=1 FLASK_ENV=development python run.py

# Artifacts on failure: e2e/test-results/ (trace, video, screenshot)
# View trace: playwright show-trace e2e/test-results/.../trace.zip
```

## Architecture

```
e2e/
  config.py           # URLs, timeouts, Stripe detection
  conftest.py         # Fixtures, cleanup registry, fixture files
  pages/              # Page Object Model (selectors)
  workflows/          # Composable journeys (author / buyer)
  support/            # User factory, DB cleanup, Stripe helper
  tests/              # Pytest modules by workflow slice
```

### Partial vs full workflows

Tests are **composable slices**, not one giant journey. Three layers:

1. **Pages** (`e2e/pages/`) — one screen (e.g. `LoginPage.login()`)
2. **Workflows** (`e2e/workflows/`) — call steps à la carte (`login()`, `setup_profile()`, `list_digital_book()`) or chained (`full_digital_listing()`)
3. **Tests** (`e2e/tests/`) — each file chooses how many steps to run

| Test file | Standalone slice |
|-----------|----------------|
| `test_login_buyer.py` | Buyer login only |
| `test_auth.py` | Register + login (author) |
| `test_author_profile.py` | Login + profile |
| `test_author_create_book.py` | Login + profile + create book |
| `test_author_digital_listing.py` | Login + profile + digital list (`slow`) |
| `test_payout.py` | Payout setup + Connect (`stripe`) |
| `test_author_campaign.py` | Launch campaign |
| `test_campaign_funding.py` | Fund campaign (`stripe`) |
| `test_reader_account.py` / `test_author_account.py` | Account settings |
| `test_edit_book.py` | Edit listing |
| `test_buyer_purchase.py` | Ebook / audiobook / bundle (`stripe`) |
| `test_audiobook.py` | Audiobook player + TTS (`slow`) |
| `test_ai_assistant.py` | Gemini assistant (`ai`) |
| `test_journey_author_written.py` | Full written-book journey |
| `test_journey_author_upload.py` | Full upload journey |
| `test_full_parallel_workflow.py` | Full author/buyer journeys |

Skip earlier steps with **`test_author` / `test_buyer`** fixtures (DB-seeded users) or pass **`login=False`** to `setup_profile()` when already logged in.

```bash
# Login only
pytest -c e2e/pytest.ini e2e/tests/test_login_buyer.py -v

# Auth (register + login)
pytest -c e2e/pytest.ini e2e/tests -m auth

# Author steps without slow uploads
pytest -c e2e/pytest.ini e2e/tests -m "author and not slow"

# Full cross-role journey
pytest -c e2e/pytest.ini e2e/tests -m full_workflow
```

| Marker | What it covers |
|--------|----------------|
| `smoke` | Fast sanity (auth, navigation) |
| `auth` | Register + login |
| `author` | Profile setup, create book, digital listing |
| `buyer` | Marketplace, library, campaigns |
| `stripe` | Stripe Checkout (needs test keys) |
| `full_workflow` / `journey` | Cross-role end-to-end |
| `payout` | Stripe Connect payout |
| `campaign` | Patron campaigns |
| `audiobook` | Audiobook generation |
| `ai` | Writing assistant |
| `account` | Account settings |
| `edit` | Book edit |
| `slow` | Upload / server processing |

```bash
# Standalone examples
pytest -c e2e/pytest.ini e2e/tests/test_payout.py -v
pytest -c e2e/pytest.ini e2e/tests/test_campaign_funding.py -v
pytest -c e2e/pytest.ini e2e/tests/test_journey_author_written.py -m journey -v
```

### Cleanup

By default **`E2E_CLEANUP=0`** — test data is kept; IDs are logged to `e2e/.e2e-created-ids.json`.

```bash
python scripts/cleanup_e2e_data.py --dry-run
CONFIRM_E2E_CLEANUP=YES python scripts/cleanup_e2e_data.py
E2E_CLEANUP=1 pytest -c e2e/pytest.ini e2e/tests -m smoke   # auto-delete after tests
```

When `E2E_CLEANUP=1`, `user_registry` calls `delete_user_and_all_data()` which removes:

- `users`, `writers`, `book_platform_users`
- All `book_projects` and related purchases, campaigns, files

Test usernames are prefixed with `e2e` (configurable via `E2E_TEST_PREFIX`) for safe identification.

### Parallel runs

Use `pytest-xdist` (`-n auto`). Each worker gets a unique `worker_id` in usernames to avoid collisions.

## CI

Pull requests to `enhancements` or `main` run [`.github/workflows/e2e.yml`](../.github/workflows/e2e.yml):

- PostgreSQL service container + Flask on `127.0.0.1:5000`
- `pytest -m "not stripe and not slow"`

Stripe and slow upload tests remain manual/local with proper secrets.
