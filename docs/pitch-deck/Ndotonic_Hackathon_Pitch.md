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

**Ndotonic** builds the AI-native author platform, live at **ndotonic.com**

*Hackathon pitch · see also `Ndotonic.md` and `PROJECT_STORY.md`*

---

## Inspiration

**Lack of funding, exposure, and editorial gates** keep impactful stories uncovered.

Before transitioning into tech, I worked as a **journalist**. I spoke with people to understand the life stories that shaped them. Independent authors told us the same pain again and again: being heard meant stitching together a dozen products just to ship one book.

| Area | Pain |
|------|------|
| **Discovery & funding** | Campaigns on one platform, pitches on another |
| **Writing & editing** | Manuscript tools, AI, and editors scattered |
| **Publishing** | ISBN, ebook, print, audiobook in separate tools |
| **Promotion** | No owned broadcast; rent attention at high cost |
| **Sales** | Digital, audio, and print in separate channels |

Especially acute in **languages and regions** where funding is scarce, exposure is limited, and traditional publishing gates are high.

---

## What it does

**Ndotonic** replaces the patchwork of Kickstarter, Google Docs, KDP, separate audiobook tools, and social promotion with one workflow:

**Pitch → Fund → Write → Publish → GLC Media → Monetize**

### Four pillars

| | |
|---|---|
| **01 · Get Discovered** | Upload a pitch and launch patron book-funding campaigns |
| **02 · Promote your book story** | **GLC Media** radio & TV stream promoting authors' stories |
| **03 · Self publish** | Ink Studio, AI editing, ISBN, ebook · print · **AI-narrated audiobook** |
| **04 · Monetize your work** | Marketplace: digital editions, audiobooks, print worldwide |

Democratize knowledge sharing through **real-life stories**, not generic content farms.

---

## How we built it

Source: `PROJECT_STORY.md`

| Layer | Technology |
|-------|------------|
| Backend | Flask, SQLAlchemy, Flask-Login |
| Database | PostgreSQL |
| Payments | Stripe (marketplace, campaigns, payouts) |
| AI writing | Google **Gemini API** (grammar, craft review, chat, covers) |
| Audiobook | Google Cloud **Text-to-Speech** (Neural2 voices) |
| Live radio | **Icecast** server (Docker), Liquidsoap, nginx on-site |
| Live TV | **HLS** pipeline on the GLC Media stack |
| Realtime | Flask-SocketIO |
| Deploy | Docker Compose, GitHub Actions → **GCP VM** |
| Infra | VPC, Cloud DNS (ndotonic.com), IAM service accounts |

### Six product surfaces shipped

Ink Studio · Publishing pipeline · Audiobook studio · Marketplace · Patron campaigns · **GLC Media**

**GLC live on the site:** dedicated **Icecast** for radio · **HLS** for TV · ADK agents for news production

---

## How we built it · AI inside Ink Studio

Purpose-built tools inside **Ink Studio**, not generic chat.

| Copy editing | Craft review | Author workflow |
|--------------|--------------|-----------------|
| Grammar & punctuation | Plot continuity | Chapter editor + versions |
| Spelling | Pacing & tension | Collaborators & beta readers |
| Linguistic errors | Narrative style | Publishing pipeline |

**Audiobook studio:** authors choose sections, pick a Neural2 voice, generate in background, preview, then publish. **Author controls inclusion**, not auto-selected chapters.

**GLC radio:** Google **ADK** agents search news, reporter agents write scripts, anchor agent coordinates the show, Cloud TTS narrates, assembly agent produces the broadcast.

---

## Author journey we optimized

```
Sign up → Create book → Write sections in Ink Studio
→ Review & accept listing terms → Publish ebook
→ Open Audiobook studio → Select sections → Generate → Publish audiobook
→ Marketplace listing live → GLC Media promotes the story
```

**Listing trust:** rights warranty, takedown consent, and AI attestation at publish time.

Like [Civil Dialog](https://devpost.com/software/civil-dialog) uses AI to improve posts **before** they go public, Ndotonic uses AI to improve manuscripts **before** books go live, with the author in control.

---

## Challenges we faced

**1. GLC radio and TV on a modern web stack**  
ADK agents, Gemini, Cloud TTS, and audio assembly had to run on **modern web infrastructure**. We tweaked radio and TV scripts and service wiring until GLC pipelines spun up reliably on our production servers.

**2. Docker Compose vs serverless**  
Ink Studio, marketplace, campaigns, PostgreSQL, nginx, realtime, and GLC generation **depend on each other**. Serverless was tempting for cost, but forced **isolated containers** and broke compose-style orchestration. **Docker Compose on a GCP VM** kept the platform logic intact.

**3. Solopreneurship**  
Solo founder: product, infra, AI, deploys, business registration, marketing, and hackathon prep, **every task figured out alone**.

**4. Trust and compliance at publish time**  
Rights warranty, takedown consent, and AI attestation at listing, while policy still catches up to AI-assisted publishing.

---

## What we're proud of

**Putting it all together.** Not a prototype.

### Shipped at ndotonic.com
Ink Studio · Patron campaigns · Marketplace · AI editing (6 modes) · **Audiobook studio** · Stripe payouts · Publishing pipeline · Analytics · Docker + CI/CD

### GLC Media
Radio & TV stream · Content hub & podcasts · Live broadcast · Editorial amplification

**Mission:** Uncover hidden potential and amplify unheard voices, including **Kinyarwanda** and **Kirundi**.

**Agents that ship and secure:** ADK GLC news production · Cursor security auditor and remediation on deploy.

---

## What's next

From `Ndotonic.md` vision:

| Year 1 | Year 2 | Year 3 |
|--------|--------|--------|
| Author acquisition · campaign GMV · workflow validation | GLC Media audience · audio/print scale | Rights & adaptation pipeline |

**Near term:** first author cohort, GLC audience growth, hire co-founder CTO and engineers.

**Honest stage:** bootstrapped founder-built platform, refining the full author journey before marketing at large scale.

Turn **unheard voices** into published books, especially where **publishing gatekeepers and distribution** have not caught up to the stories communities already tell.

---

## Built with

Python · Flask · PostgreSQL · Docker · GitHub Actions  
Google Cloud · Compute Engine · VPC · Cloud DNS · IAM · Cloud TTS  
**Gemini API** · Google ADK · Stripe · Flask-SocketIO · Cursor agents

---

<!-- _class: lead -->

## Try it out

### **ndotonic.com**

**Email:** info@ndotonic.com  
**Phone:** 628-270-1430  
**Instagram:** @ndotonic_

*Turning stories into published books.*
