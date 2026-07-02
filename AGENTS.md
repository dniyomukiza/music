# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Flask monolith ("Ink Studio" / `glconnect`) plus a small FastAPI vocabulary service. There are **no automated tests and no linter configured**.

### Services

| Service | Command (from repo root, venv active) | Port | Notes |
| --- | --- | --- | --- |
| Flask web app (main) | `python run.py` | 5000 | Entry point `run.py` → `glconnect.create_app()`. Serves the whole site + Ink Studio (`/mybook/...`). Health: `GET /health`. |
| FastAPI vocabulary/Live service | `uvicorn glconnect.voc:app --host 0.0.0.0 --port 8002` | 8002 | Defined in `glconnect/voc.py`. Health: `GET /health`. Optional for most flows. |

The Docker/Compose stack (`docker-compose.yml`) also defines nginx, icecast2, liquidsoap, certbot — these are production-only and not needed for local development.

### Environment setup (already baked into the VM snapshot)

- **Python**: a venv lives at `.venv` (Python 3.12). The Dockerfile pins 3.10, but all pinned deps install and run fine on 3.12. Activate with `. .venv/bin/activate`.
- **PostgreSQL 16** is installed locally. It is **not auto-started** on boot — start it each session with:
  `sudo pg_ctlcluster 16 main start`
  A database `glconnect` (owner role `glconnect`, password `glconnect`) already exists and persists in the snapshot (the app runs `db.create_all()` on startup, so tables are created automatically — no migration step required for a basic run).
- **`.env`** (git-ignored, persisted in the snapshot) holds local config, including `DB_URL`/`DATABASE_URL` pointing at the local Postgres. The URL **must include `?sslmode=disable`** because the app appends `sslmode=require` when `sslmode` is absent, and the local Postgres has no SSL.
- `ffmpeg` and `nodejs` are installed (used by audio / yt-dlp features).

### Non-obvious gotchas

- **No hot reload**: `run.py` disables the Werkzeug reloader on purpose. After changing Python code or `.env`, you must **restart the `python run.py` process** for changes to take effect.
- **reCAPTCHA on auth forms**: `RegistrationForm`/`LoginForm` (and others) use `flask_wtf` `RecaptchaField`.
  - Server-side validation passes whenever `current_app.testing` is true, OR when a non-empty `g-recaptcha-response` is POSTed and `RECAPTCHAPRIV` is set to Google's reCAPTCHA **test secret** (already in `.env`). So scripted/end-to-end tests can register/log in by POSTing `g-recaptcha-response=anything`.
  - In a **real browser**, the reCAPTCHA widget rejects the Google test *site* key on `localhost` ("ERROR for site owner: Invalid site key"), so the registration UI cannot be completed in-browser without real keys. `login.html` does not even render the widget. To exercise authenticated UI flows, register/confirm a user programmatically (or via the email-confirm link route `GET /routes1/confirm/<token>`, which confirms **and** logs the user in with no captcha), then drive the rest of the UI.
- **AI / email features** (Gemini, Google TTS, Mailtrap, Stripe) are optional and disabled unless their API keys are added to `.env`; the app starts and core book/marketplace flows work without them.

### Quick verification

```bash
. .venv/bin/activate
curl -s http://localhost:5000/health      # Flask
curl -s http://localhost:8002/health      # FastAPI
```
