# Testing Framework Design

End-to-end testing for the book platform (`/mybook`) and auth routes (`/routes1`). There is **no separate unit/integration test suite** under `glconnect/` today.

## Stack

| Component | Choice |
|-----------|--------|
| Runner | [pytest](https://docs.pytest.org/) |
| Browser | [Playwright](https://playwright.dev/) (Chromium, sync API) |
| Plugins | `pytest-playwright`, `pytest-xdist` (optional parallel) |
| Target | Live Flask app + configured PostgreSQL (not in-process test client) |

Quick start: see [`e2e/README.md`](../e2e/README.md).

## Architecture

```
e2e/
  config.py           # URLs, timeouts, Stripe detection
  conftest.py         # Fixtures, health check, cleanup registry
  pytest.ini          # Markers and defaults
  run_tests.sh        # Health pre-check + default pytest invocation
  pages/              # Page Object Model (selectors)
  workflows/          # Composable journeys (author / buyer)
  support/            # User factory, DB cleanup, Stripe helper
  tests/              # Pytest modules by workflow slice
  fixtures/           # cover.png, sample_ebook.txt (auto-generated)
```

### Data flow

1. **Session**: `e2e_config` fixture calls `GET /health`; skips entire session if app is down.
2. **Users**: Created via UI (`RegisterPage`) or direct DB seed (`seed_user_in_db`).
3. **Browser**: Page objects drive UI; workflows compose multi-step journeys.
4. **Teardown**: `user_registry` tracks `user_id`s; deletes when `E2E_CLEANUP=1`, else appends to `e2e/.e2e-created-ids.json`.

### Layer responsibilities

| Layer | Role |
|-------|------|
| **Config** (`e2e/config.py`) | Loads `.env`; `E2EConfig` (base URL, timeouts, `stripe_enabled` when `sk_test_*` is set) |
| **Fixtures** (`e2e/conftest.py`) | `worker_id`, `test_author` / `test_buyer`, Playwright `page` / `context` |
| **Pages** (`e2e/pages/`) | Selectors and UI actions per screen |
| **Workflows** (`e2e/workflows/`) | `AuthorWorkflow`, `BuyerWorkflow` — partial or full journeys |
| **Support** (`e2e/support/`) | User factory, cleanup, Stripe Checkout helper, app health |
| **Tests** (`e2e/tests/`) | Thin pytest modules that call workflows and assert outcomes |

## Pytest markers

Defined in [`e2e/pytest.ini`](../e2e/pytest.ini) (`--strict-markers`):

| Marker | Purpose |
|--------|---------|
| `smoke` | Fast sanity (auth, navigation) |
| `auth` | Registration and login |
| `author` | Profile setup, create book, digital listing |
| `buyer` | Marketplace, library, campaigns |
| `stripe` | Stripe Checkout (requires `sk_test_...` keys) |
| `full_workflow` | Cross-role end-to-end (parallel-friendly) |
| `journey` | Full author written/upload journeys |
| `slow` | Uploads or long server processing |
| `payout` | Stripe Connect payout setup |
| `campaign` | Patron campaign create and fund |
| `audiobook` | Audiobook generation and player |
| `ai` | Gemini writing assistant |
| `account` | Reader or author account settings |
| `edit` | Author book listing edit |

**Default local run** (`./e2e/run_tests.sh`): `-m "not stripe"` — payment tests excluded unless you opt in.

### Standalone slices (run any feature alone)

Each module is independent — prerequisites come from DB fixtures, not prior test files.

```bash
pytest -c e2e/pytest.ini e2e/tests/test_payout.py -v
pytest -c e2e/pytest.ini e2e/tests/test_campaign_funding.py -v
pytest -c e2e/pytest.ini e2e/tests/test_edit_book.py -v
pytest -c e2e/pytest.ini e2e/tests/test_journey_author_written.py -m journey -v
```

### Manual cleanup (default: keep data)

By default `E2E_CLEANUP=0` — tests log created user IDs to `e2e/.e2e-created-ids.json` without deleting.

```bash
python scripts/cleanup_e2e_data.py --dry-run
CONFIRM_E2E_CLEANUP=YES python scripts/cleanup_e2e_data.py
E2E_CLEANUP=1 pytest -c e2e/pytest.ini e2e/tests/test_auth.py -v   # auto-delete after each test
```

## Partial vs full workflows

You do **not** need to run login → profile → book → marketplace every time.

| Layer | Location | Use for |
|-------|----------|---------|
| Pages | `e2e/pages/` | Single-screen actions (`LoginPage`, `SetupProfilePage`, …) |
| Workflows | `e2e/workflows/` | Optional chains: `AuthorWorkflow.login()`, `setup_profile(login=False)`, `full_digital_listing()` |
| Tests | `e2e/tests/` | Pick slice depth per module |

**Skip account creation:** use `test_author` / `test_buyer` fixtures (DB seed).

**Skip redundant login:** after `wf.login(user)`, call `wf.setup_profile(..., login=False)`.

```bash
pytest -c e2e/pytest.ini e2e/tests/test_login_buyer.py -v    # login only
pytest -c e2e/pytest.ini e2e/tests -m auth                   # register + login
pytest -c e2e/pytest.ini e2e/tests -m "author and not slow"   # profile/create without upload
pytest -c e2e/pytest.ini e2e/tests -m full_workflow          # entire journey
```

## Test inventory

| Module | Markers | Coverage |
|--------|---------|----------|
| `test_login_buyer.py` | `smoke`, `auth`, `buyer` | Buyer login only → marketplace |
| `test_auth.py` | `smoke`, `auth` | UI register + login; seeded author reaches setup profile |
| `test_author_profile.py` | `author` | Login + profile |
| `test_author_create_book.py` | `author` | Login + profile + in-platform book |
| `test_author_digital_listing.py` | `author`, `slow` | Login + profile + digital upload → marketplace |
| `test_buyer_purchase.py` | `buyer`, `stripe` | Author lists → buyer purchases via Checkout |
| `test_payout.py` | `payout`, `stripe` | Payout setup, Connect onboarding, earnings |
| `test_author_campaign.py` | `campaign` | Launch campaign; negative upload-only gate |
| `test_campaign_funding.py` | `campaign`, `stripe` | Discover and fund campaign |
| `test_reader_account.py` | `account`, `buyer` | Reader account form |
| `test_author_account.py` | `account`, `author` | Author setup-profile update |
| `test_edit_book.py` | `edit` | Edit listing metadata |
| `test_journey_author_written.py` | `journey`, `slow` | Register → chapter → campaign → publish |
| `test_journey_author_upload.py` | `journey`, `slow` | Full digital upload journey |
| `test_audiobook.py` | `audiobook`, `slow` | Player + optional TTS generation |
| `test_ai_assistant.py` | `ai` | Gemini API + editor toolbar |
| `test_buyer_campaign.py` | `campaign`, `buyer` | Campaign discovery |
| `test_buyer_purchase.py` | `buyer`, `stripe` | Ebook, audiobook, bundle purchase |
| `test_full_parallel_workflow.py` | `full_workflow`, `slow`, `stripe` | Author listing + buyer purchase |

## Environment and app hooks

| Variable / hook | Purpose |
|-----------------|---------|
| `E2E_TESTING=1` | Skips registration reCAPTCHA (`glconnect/routes1.py`) |
| `GET /health` | Pre-flight check (`glconnect/routes.py`) |
| `E2E_BASE_URL` | App URL (default `http://localhost:5000`) |
| `STRIPE_CONNECT_ALLOW_PLATFORM_ONLY=1` | Authors can list without Connect onboarding |
| `E2E_TEST_PREFIX` | Username prefix for cleanup (default `e2e`) |
| `E2E_CLEANUP` | `1` = delete tracked users after each test; `0` = keep (default) |

## Data isolation

- **User naming**: `{prefix}-{label}-{worker_id}-{uuid8}` (max 40 chars).
- **Parallel runs**: `pytest-xdist` embeds `worker_id` in usernames to avoid collisions.
- **Cleanup**: `UserRegistry` → `delete_users_by_ids()` → `glconnect/user_deletion_handler.py`.
- **Shared DB**: E2E uses the app’s configured database; teardown is per tracked user, not a disposable DB.

## CI

GitHub Actions workflow [`.github/workflows/e2e.yml`](../.github/workflows/e2e.yml) runs smoke + non-Stripe author/buyer tests on pull requests:

- Spins up PostgreSQL service container
- Starts Flask with `E2E_TESTING=1`
- Runs `pytest -m "not stripe and not slow"`

Deploy workflow (`.github/workflows/deploy.yml`) does **not** replace E2E; it only deploys and post-deploy health-checks.

## Gaps and limitations

- No unit tests for routes, utils, or models
- Audiobook full TTS generation needs `GOOGLE_APPLICATION_CREDENTIALS` / `tts.json`
- AI tests need `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- Stripe tests need `sk_test_...` and matching `FRONTEND_BASE_URL`
- Reader vs author nav (GLC branding, `/mybook/account`) — page objects should not assert on "Ink Studio" for buyer flows

## Commands reference

```bash
# Prerequisites
E2E_TESTING=1 FLASK_ENV=development python run.py

# Default (no Stripe)
./e2e/run_tests.sh

# By marker
pytest -c e2e/pytest.ini e2e/tests -m author
pytest -c e2e/pytest.ini e2e/tests -m stripe
pytest -c e2e/pytest.ini e2e/tests -m full_workflow -n 2

# Headless (background, default CI/local)
./e2e/run_tests.sh

# Visible browser (watch tests, trace/video on failure)
./e2e/run_tests_browser.sh
./e2e/run_tests_browser.sh e2e/tests/test_auth.py -v
playwright show-trace e2e/test-results/<run>/trace.zip
```
