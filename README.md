# Ndotonic

**Turning stories into published books.**

Live product: [ndotonic.com](https://ndotonic.com)

Ndotonic is an author platform that takes a story from first pitch to paying reader in one place: patron funding, AI-assisted writing and publishing, marketplace sales, and owned promotion through **GLC Media** (radio and TV)—instead of stitching together a dozen tools.

## What it does

**Pitch → Fund → Write → Publish → GLC Media → Monetize**

| Stage | What authors get |
|--------|------------------|
| **Get discovered** | Patron book-funding campaigns from a story pitch |
| **Promote** | GLC Media radio and TV that surface authors’ stories to a live audience |
| **Self-publish** | **Ink Studio**—manuscript editing, ISBN, ebook, print, and AI-narrated audiobook |
| **Monetize** | Marketplace for digital editions, audiobooks, and print |

**Surfaces in one workflow:** Ink Studio · Publishing pipeline · Audiobook studio · Marketplace · Patron campaigns · GLC Media (content hub, podcasts, live radio, HLS TV)

**AI (Gemini)** supports grammar and craft review, cover generation, narration suggestions, and trust checks at publish time—with the **author in control**.

## Mission

Uncover hidden potential and amplify unheard voices—especially creators and languages underserved by traditional publishing.

## Built with

- **App:** Python, Flask, PostgreSQL, Flask-SocketIO
- **Infra:** Docker, nginx, GitHub Actions, Google Cloud (Compute Engine, Cloud TTS, IAM)
- **AI (product):** Gemini API, Google ADK
- **AI (development):** GPT-5.6 Terra in Cursor; Codex as a Cursor plugin
- **Media:** Icecast, Liquidsoap (live radio / TV)
- **Payments:** Stripe

## How this platform was built (AI-assisted development)

Ndotonic’s Ink Studio workflow and database layer were refactored with AI pair-programming inside **Cursor**.

### GPT-5.6 Terra (main model in Cursor)

**GPT-5.6 Terra** was the primary model for day-to-day work in Cursor—used as the main model for all interactions while building and refining the platform. That includes:

- Refactoring the **Ink Studio** author workflow (create → write → publish ebook → AI audiobook → marketplace)
- Improving **database structure** with a focus on **efficiency** (cleaner schemas, safer queries, fewer round-trips) and **security** (tighter access patterns, safer session/transaction handling, clearer boundaries around author and marketplace data)

The same Terra model was also used **inside Codex** for deeper refactors, and in the **ChatGPT Playground as a plugin** to answer prompts related to **Devpost existing projects** (hackathon submission context, project positioning, and related write-ups).

### Codex (plugin in Cursor)

**Codex** was used as a **plugin / extension inside Cursor**—not as a separate IDE. In that setup, Codex helped drive larger structural changes: database refactoring and Ink Studio workflow improvements, with GPT-5.6 Terra as the model powering those sessions.

| Tool | Where it ran | Role |
|------|----------------|------|
| **GPT-5.6 Terra** | Cursor (main model for all interactions) | Primary coding partner across the stack |
| **GPT-5.6 Terra** | Inside Codex | Same model for deeper structural refactors |
| **GPT-5.6 Terra** | ChatGPT Playground (plugin) | Answer prompts related to Devpost existing projects |
| **Codex** | Cursor plugin | Refactor DB structure + Ink Studio workflow |

## Setup instructions

### Prerequisites

- Python 3.11+ (or the version your environment already uses)
- Docker and Docker Compose (recommended for local parity with production)
- PostgreSQL (via Compose or an existing `DATABASE_URL`)
- A filled `.env` (never commit secrets)

### 1. Clone and environment

```bash
git clone <your-repo-url>
cd music-1   # or your local project folder name

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

cp .env.example .env
```

Edit `.env` and set at least:

- `SECRET_KEY`
- `DATABASE_URL` / `DB_URL`
- Stripe keys (`STRIPE_SECRET_KEY`, webhook secret as needed)
- AI keys used by the product (`GEMINI_API_KEY` / `GOOGLE_API_KEY`)
- Optional: Google Cloud credentials for TTS (`GOOGLE_APPLICATION_CREDENTIALS`)

See `.env.example` for the full list of variables and comments.

### 2. Install dependencies

```bash
pip install -r requirements.txt
# If you also run FastAPI/media helpers locally:
# pip install -r requirements-fastapi.txt
```

### 3. Run the app

**Docker Compose (recommended):**

```bash
docker compose up --build
```

The app listens on the host mapping defined in `docker-compose.yml` (Flask/SocketIO typically on port **5000** inside the container). Health checks hit `/health`.

**Local Flask entrypoint:**

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
python run.py
```

Open the app in your browser (e.g. `http://localhost:5000`). Production site: [ndotonic.com](https://ndotonic.com).

### 4. Database migrations

Apply SQL / Python migrations under the repo root and `migrations/` as needed for your environment (see `MIGRATION_INSTRUCTIONS.md` and scripts such as `run_migration.sh`). Prefer running migrations against a non-production database first.

### 5. Secrets and production notes

- Keep `.env`, `tts.json`, Stripe keys, and cookie files **out of git**.
- On Render / cloud hosts, bind HTTP to `0.0.0.0:$PORT` and treat the filesystem as ephemeral—use Postgres and object storage for durable data.
- Stripe keys with IP allowlists must include the server’s **outbound** egress IP.

## Product demo (AI-narrated)

The product demo video is:

```text
docs/demo-ai/ndotonic_demo_hybrid.mp4
```

It was produced with **GPT-5.6 Terra** for the product walkthrough and AI narration (Ink Studio → publish → audiobook → marketplace, with browser footage). Watch it locally, or open `docs/demo-ai/index.html`.

## License / hackathon

Built as a live production platform participating in a hackathon. For access questions or collaboration, contact the repository owner.
