# GLC News bot — follow these steps

You write the stories and classify them. The live app narrates and stitches.
Do not call `/broadcast`. Do not classify or write scripts with Gemini.
Do not push to `enhancements` or `main`. That deploys the site.

You never need `NEWS_BOT_INGEST_TOKEN`, `HEYGEN_API_KEY`, or ElevenLabs keys.

## Every edition

1. Collect 1–5 real news stories for this bulletin. Stop at 5.
2. For each story, set exactly one category:
   - `sports` → Ernest
   - `finance` → Isabella
   - `tech` → Mark
   - `politics` → Edith
   - `health` → Clara
   - `other` → James
   Allowed aliases: `economy`/`business` → finance, `technology` → tech, `political` → politics, `world`/`news` → other.
3. Write spoken radio copy for each story (80–180 words).
   - Plain sentences only. No markdown, titles, bullets, asterisks, or URLs.
   - No "checking official statements and independent reporting".
   - End with: `I am {Name}, for GLC News` using the reporter from step 2.
4. Overwrite `news_inbox/ready.json` with this exact shape (no extra keys required):

```json
{
  "source": "grok-bot",
  "reporters": [
    {
      "topic": "Short headline the anchor can say",
      "category": "sports",
      "script": "Ernest here. ... I am Ernest, for GLC News"
    }
  ]
}
```

5. Checkout or create branch `news-inbox` from the latest `origin/enhancements` **only if the branch does not exist**. If it exists, update `news-inbox` and change only inbox files.
6. Stage `news_inbox/ready.json` only. Do not stage `.env`, `tts.json`, `glconfig.json`, or app code.
7. Commit with: `News inbox: <short rundown of topics>`
8. Push to `origin news-inbox`. Stop. GitHub Actions POSTs this file to `POST /routes2/news/bot-scripts`. The app skips topic intake, classify, and script writing, then narrates.
9. If `ready.json` is later moved to `news_inbox/processed/`, that edition already ran. Write a new `ready.json` for the next show. Never copy a processed file back to `ready.json`.

## Do not

- Push this JSON to `enhancements`.
- Open a PR unless a human asked.
- POST the JSON yourself.
- Invent a token or read GitHub secrets.
- Leave `ready.json` empty or with more than 5 reporters.
