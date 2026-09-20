# GLC News inbox — essentials

Write the bulletin JSON. The live app narrates and stitches.
Do not call `/broadcast`. Do not push to `enhancements` or `main`.

## Shape (locked)

Overwrite `news_inbox/ready.json` only:

- `source`: `"newsroom-agent"`
- `anchor.intro`: `{TIMECHECK}` + natural welcome + concrete rundown (fresh wording each show; light "In politics… / In tech…" OK; never stiff "N stories from tech")
- `anchor.outro`: thank last reporter + close (vary wording each show)
- `reporters[]`: one block per reporter/category
  - `reporter`, `category`, `handoff`, `stories[]`, `signoff` (`I am {Name}, for GLC News.`)
  - each story: `topic` + narration-only `script` (no "Name here." / no signoff inside script)
  - 2nd+ story in a block: optional `bridge` (story-specific, not category-labeled)

## Category → reporter

- sports → Ernest
- finance → Isabella (`economy`/`business` → finance)
- tech → Mark (`technology` → tech)
- politics → Edith (`political` → politics)
- health → Clara
- other → James (`world`/`news` → other)

## Git

1. Use branch `news-inbox` (create from `origin/enhancements` only if missing).
2. Stage `news_inbox/ready.json` only for shows (docs updates may include `BOT_INSTRUCTIONS.md` / `ready.example.json`).
3. Commit: `News inbox: <short rundown>`
4. Push `origin news-inbox`. Stop. No PR unless asked. No self-POST.
5. If `ready.json` moves to `news_inbox/processed/`, write a new `ready.json` next show. Never restore processed files.
