# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Flask monolith ("GLC" / "Ink Studio") plus optional production-only
side services. The startup VM update script already installs system + Python dependencies and
sets up a local PostgreSQL; the notes below are the non-obvious things needed to run/test it.

### What the product is
- One Flask + Flask-SocketIO app (`run.py` → `create_app()` in `glconnect/__init__.py`) serving
  on `0.0.0.0:5000`. It contains everything: Ink Studio book platform (`/mybook/*`), music
  (`/music/*`), AI news (`/routes2/news/*`), blogs (`/blog/*`), dictionary (`/routes1/words`),
  auth (`/routes1/login`, `/routes1/register`). Health check: `GET /health`.
- The other `docker-compose.yml` services (FastAPI `glconnect/voc.py` on `:8002`, `icecast2`,
  `liquidsoap`, `nginx`, `certbot`) are OPTIONAL / production-only and are not needed to run or
  test the core product.

### Running the app (dev mode)
- Use the venv created by the update script: `.venv/bin/python run.py` (binds `0.0.0.0:5000`).
  Do not use Docker for local dev here — running `run.py` directly is the dev path.
- `FLASK_ENV=development` (set in `.env`) enables HTTP-friendly cookies. The reloader is
  intentionally disabled in `run.py`; restart the process manually after code changes.

### Database (the only hard startup dependency)
- The app raises `RuntimeError` at startup if `DB_URL` is unset, and it connects to Postgres
  during `create_app()` (it runs `db.create_all()` to create the ~55 tables on an empty DB).
- A local PostgreSQL is used in this environment: role `glc` / password `glc`, database
  `glconnect`. The update script does NOT create these (it must stay idempotent/minimal), so if
  the DB or role is missing, recreate it with:
  `sudo -u postgres psql -c "CREATE ROLE glc LOGIN PASSWORD 'glc';"` and
  `sudo -u postgres psql -c "CREATE DATABASE glconnect OWNER glc;"`.
- Start Postgres if it isn't running: `sudo pg_ctlcluster 16 main start`.
- GOTCHA: for any `postgresql://` URL without an `sslmode`, the app auto-appends
  `sslmode=require`. Local Postgres has no TLS, so the local `DB_URL` MUST include
  `?sslmode=disable` (see `.env`), otherwise startup fails to connect.
- GOTCHA: `glconfig.json` (committed) contains a hardcoded REMOTE Render `DB_URL` used only as a
  fallback when env `DB_URL` is empty. Always keep `DB_URL` set in `.env` so the app does not try
  that remote (likely-expired) database.

### Config / secrets
- Copy `.env.example` → `.env`. Only `DB_URL`/`DATABASE_URL` are required to boot.
- API keys (Gemini/Google `GOOGLE_API_KEY`, `GEMINI_API_KEY`, Stripe `STRIPE_*`, Mailtrap
  `MAIL_TRAP`) are OPTIONAL for startup — those features degrade/fail lazily at request time,
  they do not crash boot.
- GOTCHA: the registration form (`/routes1/register`) has a reCAPTCHA field, so UI signup needs
  `RECAPTCHAPUB`/`RECAPTCHAPRIV`. For dev, use Google's official reCAPTCHA v2 TEST keys
  (`6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI` / `6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe`),
  which always validate — they're already in `.env`. The login form has no reCAPTCHA.
- Email confirmation requires Mailtrap; without it, accounts are still created and login works
  (login does NOT require `confirmed=True`).

### Tests / lint / build
- There is no automated test suite and no linter/formatter configured in this repo. For a quick
  sanity check use `.venv/bin/python -m py_compile glconnect/*.py run.py`. There is no separate
  build step for the Flask app (the Docker image build is production-only).

### Misc
- `bleach` is not in `requirements.txt`; Flask-CKEditor logs a harmless "bleach not installed"
  warning at startup and the app runs fine without it.
