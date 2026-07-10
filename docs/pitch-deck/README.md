# Ndotonic Pitch Deck — export files

Downloadable pitch deck materials for **Ndotonic** (author platform) and **GLC Media** (radio & TV stream promoting stories and books).

## Files in this folder

| File | Format | Use |
|------|--------|-----|
| `Ndotonic.md` | Marp Markdown | **Devpost-style** project story (Inspiration → What it does → Built → Challenges → Proud → Learned → Next) |
| `Ndotonic.pptx` | PowerPoint | Investor deck (regenerate via `generate_pitch_deck.py`; separate from `Ndotonic.md`) |
| `PROJECT_STORY.md` | Markdown | Source narrative: inspiration, build, challenges |
| `Ndotonic_Hackathon_Pitch.md` | Marp Markdown | Hackathon pitch (aligned with files above) |
| `Ndotonic_Hackathon_Pitch.pptx` | PowerPoint | Hackathon pitch slides |
| `HACKATHON_PITCH.txt` | Plain text | Devpost / submission copy (paste into Story fields) |

## Regenerate PowerPoint

```bash
pip install python-pptx
python scripts/generate_pitch_deck.py              # investor → Ndotonic.pptx
python scripts/generate_pitch_deck.py hackathon    # hackathon → Ndotonic_Hackathon_Pitch.pptx
```

## Export PDF from Markdown (Marp)

```bash
npx @marp-team/marp-cli docs/pitch-deck/Ndotonic.md --pdf -o docs/pitch-deck/Ndotonic.pdf
npx @marp-team/marp-cli docs/pitch-deck/Ndotonic_Hackathon_Pitch.md --pdf -o docs/pitch-deck/Ndotonic_Hackathon_Pitch.pdf
```

## Hackathon pitch outline (11 slides)

1. **Title** — Ndotonic · ndotonic.com  
2. **Inspiration** — Funding, exposure, editorial gates (`Ndotonic.md` problem)  
3. **What it does** — Four pillars (`Ndotonic.md` product)  
4. **How we built it** — Stack + GCP (`PROJECT_STORY.md`)  
5. **AI in Ink Studio** — Six editing modes (`Ndotonic.md` differentiator)  
6. **Author journey** — Publish flow + Civil Dialog parallel  
7. **Challenges** — Four challenges (`PROJECT_STORY.md`)  
8. **Proud of** — Shipped traction (`Ndotonic.md` traction)  
9. **What's next** — Year 1/2/3 vision (`Ndotonic.md` vision)  
10. **Built with** — Tech stack  
11. **Try it out** — Contact  

Plain text version: `HACKATHON_PITCH.txt`

## Ndotonic.md outline (Devpost format)

Matches [Snapdragon AI: Multilingual Translator](https://devpost.com/software/snapdragon-ai-multilingual-translator) story sections:

1. **Title** — tagline + ndotonic.com  
2. **Inspiration**  
3. **What it does**  
4. **How we built it**  
5. **Challenges we ran into**  
6. **Accomplishments we're proud of**  
7. **What we learned**  
8. **What's next for Ndotonic**  
9. **Built with**  
10. **Try it out**  

Plain text copy: `HACKATHON_PITCH.txt` · Source narrative: `PROJECT_STORY.md`

## Investor deck outline (`Ndotonic.pptx`)

Regenerate with `python scripts/generate_pitch_deck.py` (12 slides: problem, market, competition, ask, etc.).

## Notes

- Market stats in `Ndotonic.md` are directional; verify before investor meetings.  
- Traction reflects bootstrapped, pre-scale stage (`PROJECT_STORY.md`).  
- Hackathon narrative references [Civil Dialog](https://devpost.com/software/civil-dialog) for “AI before publish” framing.
