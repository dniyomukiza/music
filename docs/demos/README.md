# Book-writing tutorial demos (Ndotonic Author Series)

Same pipeline as the pitch-deck demos:

- **Voice:** Microsoft neural TTS via `edge-tts` (`en-US-AvaMultilingualNeural`)
- **Visuals:** 1920×1080 branded frames with **Ndotonic** wordmark + official logo
- **Transcripts:** `.srt` + `*-NARRATION.md` per lesson
- **Length:** about 3 minutes each

## Build

```bash
cd docs/demos
pip install edge-tts pillow   # once
python3 build_author_tutorials.py                  # all seven lessons
python3 build_author_tutorials.py 01-getting-started
```

Requirements: `ffmpeg`, `ffprobe`, Python 3, network access for Edge TTS.

## Outputs

| Lesson | Video | Transcript |
|--------|-------|------------|
| 01 Getting Started | `01-getting-started.mp4` | `.srt` + `-NARRATION.md` |
| 02 Narrative Structure | `02-narrative-structure.mp4` | `.srt` + `-NARRATION.md` |
| 03 Building Characters | `03-building-characters.mp4` | `.srt` + `-NARRATION.md` |
| 04 Developing Plot | `04-developing-plot.mp4` | `.srt` + `-NARRATION.md` |
| 05 Polish and Format | `05-polish-and-format.mp4` | `.srt` + `-NARRATION.md` |
| 06 Cover and Description | `06-cover-and-description.mp4` | `.srt` + `-NARRATION.md` |
| 07 How to Launch | `07-how-to-launch.mp4` | `.srt` + `-NARRATION.md` |

Edit narration strings in `build_author_tutorials.py`, then rebuild.

The idea-to-draft, narrative-structure, character, and plot lessons are adapted from [Apple Books for Authors](https://authors.apple.com/support/3971-from-idea-to-first-draft) guidance, with original narration for the Ndotonic Author Series.
