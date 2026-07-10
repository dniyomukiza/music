# Project Story — Ndotonic

## About the project

**Ndotonic** is an author platform that carries a story from first pitch to paying reader in one place. Authors can pitch ideas, run patron-funded book campaigns, write in **Ink Studio**, polish manuscripts with purpose-built AI tools, publish ebooks, print, and audiobooks to a marketplace, and promote their work through **GLC Media** (radio & TV).

Live at [ndotonic.com](https://ndotonic.com), the platform replaces the patchwork of Kickstarter, Google Docs, KDP, separate audiobook tools, and social promotion with a single, connected workflow:

**Pitch → Fund → Write → Publish → GLC Media → Monetize**

---

## What inspired us

Before transitioning into tech, I worked as a journalist. I spoke with people to understand the life stories that shaped them, and I also heard from independent authors who told us the same story again and again: being heard meant stitching together a dozen products just to ship one book. Funding lived on one site, writing on another, publishing somewhere else, audiobook production in yet another tool, and promotion depended on algorithms they did not own—especially editorial lines set by traditional publishing houses.

We were especially motivated by creators in languages and regions where traditional publishing gates are high and **published books in local languages are hard to find, fund, and distribute**, even though storytelling is already part of everyday life. We wanted a platform that democratizes knowledge sharing through real-life stories, where:

- A story pitch could attract real patron support before the manuscript was finished
- AI editing and review was **built into the writing flow**, not a generic chat sidebar
- Ebook and **AI-narrated audiobook** could ship from the same title
- Authors could **own promotion** through our integrated GLC Media (radio/TV) instead of renting attention that would otherwise require large amounts of spend

The vision was simple: **turn stories into published books**

---

## How we built it

Ndotonic is a **Python / Flask** web application with **PostgreSQL**, deployed with **Docker** and a **GitHub Actions** CI/CD pipeline to production.

### Core architecture

| Layer | Technology |
|--------|------------|
| Backend | Flask, SQLAlchemy, Flask-Login |
| Database | PostgreSQL |
| Payments | Stripe (marketplace, campaigns, payouts) |
| AI writing | Google Gemini (grammar, craft review, chat, cover generation) |
| Audiobook TTS | Google Cloud Text-to-Speech (Neural2 voices) |
| Live radio | **Icecast** server (Docker), Liquidsoap, nginx proxy on-site |
| Live TV | **HLS** pipeline (Liquidsoap video profile) |
| Realtime | Flask-SocketIO |
| Deploy | Docker Compose, GitHub Actions → server pull & rebuild |

### Major product surfaces

1. **Ink Studio** — manuscript editor with sections (chapters, foreword, appendix), collaborators, version history, and a draggable **AI Assistant** (developmental + author-editing modes).
2. **Publishing pipeline** — cover upload or AI-generated covers, ISBN pool assignment, listing terms, ebook/print/audiobook formats.
3. **Audiobook studio** — authors choose which sections to narrate, pick a voice, generate audio in the background, preview tracks, then publish to the marketplace.
4. **Marketplace & library** — discover, purchase, and read ebooks; listen to audiobooks.
5. **Patron campaigns** — pitch → fund → accountability milestones through publication.
6. **GLC Media** — content hub, podcasts, live **Icecast radio** and **HLS TV** on the site, and broadcast promotion for author stories.

### Example author flow we optimized

```
Sign up → Create book → Write sections in Ink Studio
→ Review & accept listing terms → Publish ebook
→ Open Audiobook studio → Select sections → Generate → Publish audiobook
→ Marketplace listing live
```

---

## Challenges we faced

### 1. GLC radio and TV on a modern web stack

GLC news production depends on ADK agents, Gemini, Cloud TTS, and audio assembly. Live radio and TV on the site required a dedicated **Icecast** server for GLC radio (Liquidsoap feeds the stream; nginx proxies to listeners) and an **HLS** pipeline for live TV, wired through Docker Compose alongside the web app.

### 2. Docker Compose vs serverless

Ndotonic is not one API. Ink Studio, marketplace, campaigns, PostgreSQL, nginx, realtime, and GLC generation **depend on each other**. Serverless looked ideal for cost, but it pushed every service into **isolated containers** with no shared compose graph. That broke the logic of the project. We landed on **Docker Compose on a GCP VM** so interdependent services start, talk, and recover together.

### 3. Solopreneurship

As a solo founder, I had to figure out **every task alone**: product, infrastructure, AI integration, deploys, business registration, marketing, and hackathon materials, without a co-founder network to divide the load.

### 4. Trust and compliance at publish time

Listing requires rights warranty, takedown consent, and clear AI attestation while copyright and platform policy are still catching up to AI-assisted publishing.

---

## Where we are today

Ndotonic is a **live, multi-surface author platform** — not a prototype. Ink Studio, marketplace, campaigns, AI editing, audiobook production, analytics, and GLC radio/TV promotion work together as one story.

We are continuing to refine the author journey by testing the workflow before we are ready to take first customers and do marketing at large scale.

---

*Turning stories into published books.*

**Ndotonic** · [ndotonic.com](https://ndotonic.com)
