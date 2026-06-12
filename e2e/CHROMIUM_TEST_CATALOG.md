# E2E tests — Chromium commands & expected UI

Run every test **one at a time** in a **visible Chromium** window.

## Setup (once per session)

**Terminal 1 — app**
```bash
cd "/Applications/untitled folder/music-1"
E2E_TESTING=1 FLASK_ENV=development python run.py
```

**Terminal 2 — run one test**
```bash
./e2e/run_tests_browser.sh e2e/tests/<file>::<test_name> -v
```

Optional: `E2E_SLOW_MO=800` (slower) · `PWDEBUG=1` (step through) · artifacts on failure in `e2e/test-results/`

**Needs Stripe test key** (`sk_test_*`): tests marked 🅂  
**Mostly API / little UI**: tests marked 🔌

### Credentials from `.env`

Both **Flask** (`run.py`) and **pytest** (`e2e/config.py`) load the project root **`.env`** automatically. No need to export keys manually if they are already in `.env`.

| Variable | Used for |
|----------|----------|
| `STRIPE_SECRET_FOR_TEST=sk_test_...` | 🅂 **E2E only** — pytest + `E2E_TESTING=1` Flask; production `STRIPE_SECRET_KEY` unchanged |
| `FRONTEND_BASE_URL=http://localhost:5000` | **Required** for local Stripe return URLs (not `https://glc.cool/`) |
| `STRIPE_CONNECT_ALLOW_PLATFORM_ONLY=1` | Authors can list & sell without Connect onboarding (local dev) |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | AI assistant test |
| `GOOGLE_APPLICATION_CREDENTIALS=tts.json` | Full audiobook generation test |

**Startup lines you may see (Terminal 1)**

```
DEBUG: Stripe key availability: STRIPE_SECRET_KEY=set, STRIPE_API_KEY=NOT SET
```

That is fine — only `STRIPE_SECRET_KEY` is required. Use the **secret** key (`sk_test_...`), not the publishable key (`pk_...`).

If Flask prints `Stripe: effective server key is LIVE (sk_live_...)`, add `STRIPE_SECRET_FOR_TEST=sk_test_...` and restart with **`E2E_TESTING=1`** — Flask will use the test key only in that mode.

**Check Stripe is wired before a 🅂 test (Terminal 2)**

```bash
python -c "from e2e.config import get_config; c=get_config(); print('Stripe E2E:', 'enabled' if c.stripe_enabled else 'disabled — set STRIPE_SECRET_FOR_TEST in .env')"
```

---

## Auth & login

### `test_author_can_register_and_login`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_auth.py::test_author_can_register_and_login -v
```
**Tests** — New author registers, logs in, lands on author onboarding.  
**Expected UI** — Register form → login form → **`/mybook/setup-profile`** with `#profileSetupForm` visible.

---

### `test_seeded_author_reaches_setup_profile`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_auth.py::test_seeded_author_reaches_setup_profile -v
```
**Tests** — Pre-seeded author logs in and opens profile setup.  
**Expected UI** — Login → **`/mybook/setup-profile`** with `#profileSetupForm`.

---

### `test_seeded_buyer_login_reaches_marketplace`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_login_buyer.py::test_seeded_buyer_login_reaches_marketplace -v
```
**Tests** — Pre-seeded buyer logs in.  
**Expected UI** — **`/mybook/marketplace`** with `#booksGrid` catalog visible.

---

### `test_buyer_login_via_workflow`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_login_buyer.py::test_buyer_login_via_workflow -v
```
**Tests** — Same as above via buyer workflow helper.  
**Expected UI** — **`/mybook/marketplace`** with book grid.

---

## Author — profile

### `test_author_completes_setup_profile`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_author_profile.py::test_author_completes_setup_profile -v
```
**Tests** — Author completes Ink Studio author card.  
**Expected UI** — Setup profile form submitted → redirect to **`/mybook/books`** (author hub).

---

### `test_author_updates_setup_profile`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_author_account.py::test_author_updates_setup_profile -v
```
**Tests** — Author updates pen name on profile.  
**Expected UI** — Setup profile page; **`#penName`** field shows **"E2E Pen Updated"**.

---

## Author — create & list books

### `test_author_creates_in_platform_book`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_author_create_book.py::test_author_creates_in_platform_book -v
```
**Tests** — Author creates a written (in-platform) book project.  
**Expected UI** — Create-book form → **`/mybook/books`** lists the new book title.

---

### `test_author_uploads_digital_book_to_marketplace`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_author_digital_listing.py::test_author_uploads_digital_book_to_marketplace -v
```
**Tests** — Author uploads cover + ebook and publishes listing.  
**Expected UI** — Upload form → **`/mybook/marketplace`** `#booksGrid` shows the new title.

---

## Author — edit & listing lifecycle

### `test_author_edits_digital_listing`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_edit_book.py::test_author_edits_digital_listing -v
```
**Tests** — Author changes title and price on a digital listing.  
**Expected UI** — Edit book form (`#editBookForm`); saved title ends with **`-edited`**, price **$5.99** (verified via API).

---

### `test_author_remove_listing_hides_digital_book`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_listing_lifecycle.py::test_author_remove_listing_hides_digital_book -v
```
**Tests** — Author removes a digital listing from marketplace.  
**Expected UI** — Marketplace search: **`#booksGrid` no longer contains** the book title.

---

### `test_author_unpublish_hides_written_book`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_listing_lifecycle.py::test_author_unpublish_hides_written_book -v
```
**Tests** — Author unpublishes a written book; buyer checks marketplace.  
**Expected UI** — Buyer on marketplace: search → **book title gone** from `#booksGrid`.

---

## Author — campaigns

### `test_author_launches_campaign_ui`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_author_campaign.py::test_author_launches_campaign_ui -v
```
**Tests** — Author creates a patron campaign for a written book.  
**Expected UI** — Campaign form submitted → **`/mybook/investments`** shows campaign title.

---

### `test_uploaded_book_cannot_create_campaign`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_author_campaign.py::test_uploaded_book_cannot_create_campaign -v
```
**Tests** — Digital-upload-only books cannot start a campaign.  
**Expected UI** — Visiting create-campaign URL → **redirected to book page** (`/mybook/books/<id>`), not campaign form.

---

## Author — payout & earnings

### `test_author_reaches_payout_setup`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_payout.py::test_author_reaches_payout_setup -v
```
**Tests** — Author opens Stripe Connect payout setup.  
**Expected UI** — **`/mybook/payout-setup`** with **`#btnStripeConnect`** button visible.

---

### `test_author_opens_stripe_connect_onboarding` 🅂
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_payout.py::test_author_opens_stripe_connect_onboarding -v
```
**Tests** — Author starts Stripe Connect onboarding.  
**Expected UI** — Click Connect → **new tab opens `connect.stripe.com`** (Stripe onboarding).

---

### `test_author_earnings_dashboard_loads`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_payout.py::test_author_earnings_dashboard_loads -v
```
**Tests** — Author opens sales & payouts dashboard.  
**Expected UI** — **`/mybook/earnings`** page body contains **"Earnings"**.

---

## Author — audiobook

### `test_audiobook_status_api_reachable` 🔌
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_audiobook.py::test_audiobook_status_api_reachable -v
```
**Tests** — Audiobook generation status endpoint responds.  
**Expected UI** — Author logged in; **no specific page** (API check only). Browser may flash author pages.

---

### `test_audiobook_player_with_seeded_audio`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_audiobook.py::test_audiobook_player_with_seeded_audio -v
```
**Tests** — Audiobook player loads for a book with seeded audio.  
**Expected UI** — **`/mybook/audiobook/<id>/player`** — page contains **"Audiobook"**.

---

### `test_audiobook_generation_flow`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_audiobook.py::test_audiobook_generation_flow -v
```
**Tests** — Triggers TTS audiobook generation (needs `tts.json`).  
**Expected UI** — Author book area; generation returns **processing or completed** (may take minutes).

---

## Author — AI assistant 🔌

### `test_ai_assistant_api_generates_content`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_ai_assistant.py::test_ai_assistant_api_generates_content -v
```
**Tests** — Gemini writing assistant returns text for a chapter (needs `GEMINI_API_KEY`).  
**Expected UI** — Author logged in; **API response** with generated snippet (>10 chars). No dedicated result page.

---

## Buyer — account

### `test_buyer_updates_account_profile`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_reader_account.py::test_buyer_updates_account_profile -v
```
**Tests** — Reader updates name on GLC account settings.  
**Expected UI** — **`/mybook/account`** — first name **"E2EUpdated"**, last name **"Reader"** in form fields.

---

## Buyer — marketplace discovery

### `test_marketplace_search_finds_seeded_book`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_marketplace_discovery.py::test_marketplace_search_finds_seeded_book -v
```
**Tests** — Quick search finds a pre-seeded listing.  
**Expected UI** — Marketplace `#searchInput` → **`#booksGrid` shows book title**.

---

### `test_marketplace_genre_filter_shows_seeded_book`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_marketplace_discovery.py::test_marketplace_genre_filter_shows_seeded_book -v
```
**Tests** — Genre + search URL filters show seeded book.  
**Expected UI** — Marketplace with **Fiction filter** → **`#booksGrid` shows book title**.

---

### `test_marketplace_sort_keeps_book_visible`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_marketplace_discovery.py::test_marketplace_sort_keeps_book_visible -v
```
**Tests** — Sort by lowest price still shows the book.  
**Expected UI** — Marketplace **sorted by price low** → **`#booksGrid` shows book title**.

---

## Buyer — purchases 🅂

### `test_buyer_purchases_ebook`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_buyer_purchase.py::test_buyer_purchases_ebook -v
```
**Tests** — Buyer buys digital ebook via Stripe Checkout.  
**Expected UI** — Marketplace modal → **Stripe Checkout** → success → **`/mybook/library`** lists book title.

---

### `test_buyer_purchases_audiobook`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_buyer_purchase.py::test_buyer_purchases_audiobook -v
```
**Tests** — Buyer buys audiobook format via Stripe.  
**Expected UI** — Purchase modal (audiobook selected) → Stripe → **`/mybook/library`** shows book.

---

### `test_buyer_purchases_bundle`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_buyer_purchase.py::test_buyer_purchases_bundle -v
```
**Tests** — Buyer buys ebook + audiobook bundle via Stripe.  
**Expected UI** — Bundle option in modal → Stripe → **`/mybook/library`** shows book.

---

### `test_buyer_purchases_listed_book`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_buyer_purchase.py::test_buyer_purchases_listed_book -v
```
**Tests** — Full path: author lists book in UI, buyer purchases it.  
**Expected UI** — Author upload flow → buyer marketplace purchase → Stripe → **library contains new title**.

---

## Buyer — library

### `test_buyer_reads_purchased_ebook`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_buyer_library.py::test_buyer_reads_purchased_ebook -v
```
**Tests** — Buyer opens in-app reader for owned ebook (no Stripe).  
**Expected UI** — **`/mybook/library/books/<id>/read`** — `#readerBody` visible with book title and **"E2E Sample Ebook"** text.

---

### `test_buyer_downloads_purchased_ebook`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_buyer_library.py::test_buyer_downloads_purchased_ebook -v
```
**Tests** — Buyer downloads owned digital file.  
**Expected UI** — No page change; **file download succeeds** (HTTP 200, attachment header). Playwright may not show a save dialog.

---

## Buyer — campaigns

### `test_buyer_can_open_campaign_discovery`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_buyer_campaign.py::test_buyer_can_open_campaign_discovery -v
```
**Tests** — Buyer opens campaign discovery page.  
**Expected UI** — **`/mybook/investments`** shows seeded **campaign title**.

---

### `test_buyer_finds_campaign_on_investments`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_campaign_funding.py::test_buyer_finds_campaign_on_investments -v
```
**Tests** — Live campaign visible on investments page.  
**Expected UI** — **`/mybook/investments`** body contains **campaign title**.

---

### `test_buyer_funds_campaign` 🅂
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_campaign_funding.py::test_buyer_funds_campaign -v
```
**Tests** — Buyer invests in campaign via Stripe.  
**Expected UI** — Invest flow → **Stripe Checkout** → campaign detail page shows **"$10"** funding amount.

---

## Access control

### `test_buyer_sees_glc_branding_not_ink_studio`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_access_control.py::test_buyer_sees_glc_branding_not_ink_studio -v
```
**Tests** — Reader nav brand is GLC, not Ink Studio.  
**Expected UI** — **My Library** — `.ink-lib-brand` shows **"GLC"**, not "Ink Studio".

---

### `test_author_sees_ink_studio_branding`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_access_control.py::test_author_sees_ink_studio_branding -v
```
**Tests** — Author nav brand is Ink Studio.  
**Expected UI** — **My Library** — `.ink-lib-brand` shows **"Ink Studio"**.

---

### `test_buyer_blocked_from_author_create_book`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_access_control.py::test_buyer_blocked_from_author_create_book -v
```
**Tests** — Buyer cannot access author create-book route.  
**Expected UI** — Redirected to **/mybook/setup-profile** (or login); **no "Create a new book"** form.

---

## Integration — Stripe webhook 🔌

### `test_checkout_session_completed_webhook_finishes_purchase`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_stripe_webhook.py::test_checkout_session_completed_webhook_finishes_purchase -v
```
**Tests** — Dev webhook completes a pending purchase in the database.  
**Expected UI** — **No user-facing UI**; purchase status becomes **completed** in DB. Browser opens briefly only for the HTTP POST.

---

## Full journeys

### `test_author_full_digital_listing_journey`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_full_parallel_workflow.py::test_author_full_digital_listing_journey -v
```
**Tests** — End-to-end: register → profile → upload → marketplace.  
**Expected UI** — Full author onboarding + upload → **`/mybook/marketplace`** `#booksGrid` shows new book title.

---

### `test_author_upload_to_marketplace_journey`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_journey_author_upload.py::test_author_upload_to_marketplace_journey -v
```
**Tests** — Same upload journey (alternate entry point).  
**Expected UI** — **`/mybook/marketplace`** `#booksGrid` contains journey book title.

---

### `test_author_written_book_to_publication`
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_journey_author_written.py::test_author_written_book_to_publication -v
```
**Tests** — Register → profile → book → chapter → campaign → publish.  
**Expected UI** — Long author flow → **`/mybook/marketplace`** `#booksGrid` shows published written book title.

---

### `test_buyer_marketplace_purchase_journey` 🅂
**Command**
```bash
./e2e/run_tests_browser.sh e2e/tests/test_full_parallel_workflow.py::test_buyer_marketplace_purchase_journey -v
```
**Tests** — Author lists book; new buyer registers and purchases.  
**Expected UI** — Author listing → buyer register → Stripe Checkout → **`/mybook/library`** shows purchased title.

---

## Index

| | |
|--|--|
| Total tests | **41** |
| Launcher | `./e2e/run_tests_browser.sh` |
| 🅂 Stripe | 7 tests — need `STRIPE_SECRET_KEY=sk_test_...` |
| 🔌 API-heavy | 3 tests — minimal or no UI |
