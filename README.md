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
- **AI:** Gemini API, Google ADK  
- **Media:** Icecast, Liquidsoap (live radio / TV)  
- **Payments:** Stripe  

## Quick start (local)

1. Clone the repo and create a virtualenv.
2. Copy `.env.example` → `.env` and fill in the required values (never commit `.env`).
3. Install dependencies: `pip install -r requirements.txt`
4. Run with Docker Compose or your usual Flask entrypoint (see `Dockerfile` / `docker-compose.yml`).

Secrets (API keys, database URLs, Stripe, Google credentials) belong in environment variables or server-only config—not in git.

## License / hackathon

Built as a live production platform participating in a hackathon. For access questions or collaboration, contact the repository owner.
