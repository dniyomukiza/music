---
marp: true
theme: default
paginate: true
size: 16:9
header: ''
footer: ''
style: |
  section {
    background: #060807;
    color: #e8ece9;
    font-family: 'Segoe UI', system-ui, sans-serif;
  }
  h1, h2, h3 { color: #e8ece9; }
  strong, em { color: #e0bc3a; font-style: normal; }
  section.lead h1 { font-size: 2.4rem; }
  section.lead p { color: #9aa8a0; }
  table { font-size: 0.85rem; }
  th { background: rgba(201,162,39,0.2); color: #e0bc3a; }
  td { border-color: rgba(201,162,39,0.15); }
  ul { color: #c8d0cc; }
---

<!-- _class: lead -->

# Ndotonic

## Turning **stories** into published books

Live at **ndotonic.com**

---

## Inspiration

**Lack of funding, exposure, and editorial gates** keep impactful stories uncovered.

Before transitioning into tech, I heard from independent authors who kept telling us the same thing: to ship one book they had to stitch together a dozen tools.

Funding on one site. Writing on another. Publishing elsewhere. Audiobooks production in a fourth tool. Promotion tied to algorithms and editorial gates they did not control, especially lines set by **traditional publishing houses**.

We were especially motivated by creators in languages and regions where **published books in local languages are hard to find, fund, and distribute**, even though storytelling is already part of everyday life.

We built **Ndotonic** to democratize knowledge sharing through real-life stories: patron support before the manuscript is done, AI editing inside the writing flow, ebook and **AI-narrated audiobook** from one title, and owned promotion through **GLC Media** radio and TV instead of rented attention.

**The vision:** turn stories into published books.

---

## What it does

**Ndotonic** carries a story from first pitch to paying reader in one place.

**Pitch → Fund → Write → Publish → GLC Media → Monetize**

- **01 · Get Discovered** — Patron book-funding campaigns from a story pitch
- **02 · Promote your book story** — **GLC Media** radio and TV stream authors' stories and books to a live audience
- **03 · Self publish** — **Ink Studio**, six AI editing modes, ISBN, ebook, print, **AI-narrated audiobook**
- **04 · Monetize your work** — Marketplace for digital editions, audiobooks, and worldwide print

**Six surfaces, one workflow:** Ink Studio · Publishing pipeline · Audiobook studio · Marketplace · Patron campaigns · **GLC Media** (content hub, podcasts, live **Icecast** radio, **HLS** TV, broadcast promotion)

**Ndotonic** uses **Gemini** to elevate manuscripts before books go live: grammar, craft review, covers, narration suggestions, and trust checks at publish time, with the **author in control**.

---

## Challenges we ran into

**1. GLC radio and TV on a modern web stack**
ADK agents, Gemini, Cloud TTS, and audio assembly had to run alongside dedicated broadcast infrastructure: **Icecast** for live radio and **HLS** for live TV, wired through Docker Compose and nginx next to the web app.

**2. Docker Compose vs serverless**
Ink Studio, marketplace, campaigns, PostgreSQL, nginx, realtime, and GLC generation depend on each other. Serverless forced isolated containers and broke compose-style orchestration. **Docker Compose on a GCP VM** kept interdependent services starting, talking, and recovering together.

**3. Solopreneurship**
As a solo founder, every task fell on one person: product, infrastructure, AI integration, deploys, business registration, marketing, and hackathon materials.

**4. Trust and compliance at publish time**
Listing requires rights warranty, takedown consent, and clear AI attestation while copyright and platform policy are still catching up to AI-assisted publishing.

---

## What we are proud of

**Putting it all together.**

**Ndotonic** is **live at ndotonic.com**, not a prototype. Ink Studio, patron campaigns, marketplace, six-mode AI editing, audiobook studio, Stripe payouts, publishing pipeline, analytics, and GLC radio/TV promotion work as **one author story**.

We turned what authors told us into product. AI lives inside the author workflow where craft, production, and trust decisions actually happen.

**Mission:** Uncover hidden potential and amplify unheard voices.

---

## Lessons learnt

- Orchestrating **production agents** (Gemini, ADK) takes **detailed task descriptions** and **multi-turn testing** to evaluate consistency before anything ships.

- Building solo means owning product, infra, AI, compliance, and go-to-market at once, and **shipping what validates the full journey first**.

- Every great platform starts with an idea, then the hard work of **turning it into something real**; **winning your first users** is the steepest climb, and also where the story begins to matter.

---

## Next steps

- **Year 1:** Author acquisition · campaign GMV · workflow validation
- **Year 2:** GLC Media content · audio and print scale
- **Year 3:** Rights and adaptation pipeline

---

## Built with

- Python, Flask, PostgreSQL, Docker, GitHub Actions
- Google Cloud Platform: Compute Engine, VPC, Cloud DNS, IAM, Cloud Text-to-Speech
- Gemini API, Google ADK, google.generativeai
- Icecast, Liquidsoap, Stripe, Flask-SocketIO
- AI agents
