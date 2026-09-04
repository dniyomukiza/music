# GLC Media TV: creator tools (deferred)

Status: saved for later. Do not implement until news is on air and this work is scheduled.

Locked product rule:

- **GLC Media TV:** creator submits a **trailer** only. Free on the linear stream. Discovery.
- **Marketplace:** creator sells the **full video** like an ebook or audiobook. Buyer plays it in My Library.
- The full film never goes on the 24/7 playlist.

## Why

News (HeyGen) will not fill a 24/7 HLS channel. Fill the rest of the clock with branded story films from Ink Studio creators, not a YouTube clone.

## Dayparts (wheels)

- GRO News bulletins (existing pipeline; audio stays on Google TTS — see `NEWS_PIPELINE_PLAN.md`)
- Author story films: 8–15 min memoir / documentary (HeyGen Avatar IV max 30 min per job; stitch scenes if longer)
- Kids story hour: 5–8 min illustrated/narrated
- Author desk interstitials pointing at the marketplace listing
- Music/artist clips as late-night fill

## Story Film Studio (inside Ink Studio)

1. Story bible + script (Gemini / book agent)
2. Locked character + voice (same roster pattern as `heygen_news.py`)
3. Scene render + stitch (`ffmpeg` + GLC bumpers)
4. Submit **trailer** to TV (`videolist.m3u` / `DownloadedVideo`, review-gated)
5. Sell **full video** as a new marketplace format `video` in `book_purchase_format.py`

Video royalty should track audiobook (**70/30**), not ebook 90/10, because HeyGen minutes are expensive.

## Pilot (when we implement)

One Ink Studio title end-to-end: trailer on Live TV, full film listed and purchased as `video`, playback in My Library.

Trailers may live on the linear path (`glconnect/static/ytautovid/`). Paid masters need durable storage.

## Do not build yet

- Full video editor
- Open YouTube-style platform
- Full paid films on the live playlist
- A second CMS besides Ink Studio
