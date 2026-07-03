# Ndotonic Pitch Deck — export files

Downloadable pitch deck materials for **Ndotonic** (company) and **GLC Media** (radio & TV stream promoting stories and books).

## Files

| File | Format | Use |
|------|--------|-----|
| `Ndotonic_Pitch_Deck.pptx` | PowerPoint | Open in PowerPoint, Keynote, or Google Slides (File → Import) |
| `Ndotonic_Pitch_Deck.md` | Marp Markdown | Edit slides in VS Code + Marp, or export to PDF/PPTX |
| `Ndotonic_Pitch_Deck.pdf` | PDF | Prit or email (generate with commands below) |

## Regenerate PowerPoint

```bash
pip install python-pptx
python scripts/generate_pitch_deck.py
```

Output: `docs/pitch-deck/Ndotonic_Pitch_Deck.pptx`

## Export PDF or PPTX from Markdown (Marp)

Install [Marp CLI](https://github.com/marp-team/marp-cli):

```bash
npx @marp-team/marp-cli docs/pitch-deck/Ndotonic_Pitch_Deck.md --pdf -o docs/pitch-deck/Ndotonic_Pitch_Deck.pdf
npx @marp-team/marp-cli docs/pitch-deck/Ndotonic_Pitch_Deck.md --pptx -o docs/pitch-deck/Ndotonic_Pitch_Deck_from_marp.pptx
```

Or use the **Marp for VS Code** extension: open the `.md` file → export from the Marp panel.

## Slide outline (12 slides)

1. Title — Ndotonic / GLC Media  
2. Problem  
3. Solution  
4. Product — Why Ndotonic (4 pillars)  
5. AI differentiator  
6. Market  
7. Business model  
8. Traction (platform + GLC Media)  
9. Competition  
10. Vision  
11. Team  
12. The ask  

## Notes

- Market stats are directional — replace with verified figures before investor meetings.  
- The web route `/pitch-deck` is optional; these files are the primary deliverables.
