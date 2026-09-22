#!/usr/bin/env python3
"""Generate mixed-genre radio tracks from video/radio-music-prompts.md via ElevenLabs Music."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "glconnect" / "static" / "eleven"
PLAYLIST = ROOT / "eleven.m3u"
LIQ_PREFIX = "/liqfolder/glconnect/static/eleven/"
COMPOSE_URL = "https://api.elevenlabs.io/v1/music"
MODEL_ID = "music_v2_5"

UNIVERSAL = (
    "Original radio single, no copyrighted melody or lyrics, no named artists. "
    "Hook hits by 8 to 12 seconds, no intro fluff, no long instrumental breakdown, "
    "chorus repeats at least twice, cold or fast fade ending, radio-clean lyrics, "
    "polished commercial mastering."
)

# One track per genre so a batch never stacks the same style.
BATCH_1 = [
    {
        "id": "01",
        "title": "GLC Radio - Hyper-Hook Pop",
        "genre": "pop",
        "vocal": "female",
        "music_length_ms": 105000,
        "prompt": (
            "Hyperpop-leaning mainstream pop, 128 BPM, female lead vocalist, "
            "pitched-up vocal chop hook that hits in the first 8 seconds, glossy synth stabs, "
            "four-on-the-floor kick, one pre-chorus max, chorus repeats 3 times, no bridge, "
            "radio edit 1:45, Gen-Z crossover energy."
        ),
    },
    {
        "id": "02",
        "title": "GLC Radio - Voice-Memo R&B",
        "genre": "rnb",
        "vocal": "male",
        "music_length_ms": 110000,
        "prompt": (
            "Neo-soul R&B, 84 BPM, male lead vocalist, opens cold with an a cappella riff "
            "for 4 seconds before the groove drops, silky layered vocals, Rhodes keys, "
            "trap-hi-hat undertone, one tight hook repeated twice, runtime 1:50, "
            "warm late-night radio mix."
        ),
    },
    {
        "id": "03",
        "title": "GLC Radio - 8-Bar Blitz Rap",
        "genre": "rap",
        "vocal": "female",
        "music_length_ms": 100000,
        "prompt": (
            "Uptempo trap-rap, 150 BPM, female rapper, hook drops at 0:06 over a single "
            "looped melodic sample, verses capped at 8 bars each, triplet hi-hats, "
            "chant-style ad-libs doubling as hook reinforcement, cold cut ending, "
            "runtime 1:40, radio-clean lyrics."
        ),
    },
    {
        "id": "04",
        "title": "GLC Radio - Log-Drum Afrobeats",
        "genre": "afrobeats",
        "vocal": "male",
        "music_length_ms": 110000,
        "prompt": (
            "Afrobeats, 106 BPM, smooth male vocal, log drum hook that starts before any vocal "
            "for the first 5 seconds, call-and-response ad-libs, bilingual English and Pidgin "
            "chorus, no bridge, runtime 1:50, festival-ready polish."
        ),
    },
    {
        "id": "05",
        "title": "GLC Radio - Drop-First Electro",
        "genre": "electro",
        "vocal": "female",
        "music_length_ms": 100000,
        "prompt": (
            "Electro-pop, 124 BPM, female lead vocalist, drop happens in the first 10 seconds, "
            "hook before verse, glitchy vocal chops, bright arpeggios, one short verse, "
            "second drop closes the track, runtime 1:40, festival-radio hybrid mix."
        ),
    },
    {
        "id": "06",
        "title": "GLC Radio - Modern Zouk-Love",
        "genre": "zouk",
        "vocal": "male",
        "music_length_ms": 115000,
        "prompt": (
            "Zouk, 96 BPM, male romantic breathy vocals in French and Creole-inflected English, "
            "signature syncopated zouk drum pattern, warm synth pads, guitar arpeggio hook, "
            "sensual but radio-clean, chorus repeats 3 times, runtime 1:55, "
            "Caribbean-French crossover polish."
        ),
    },
    {
        "id": "07",
        "title": "GLC Radio - Riddim-First Dancehall",
        "genre": "dancehall",
        "vocal": "female",
        "music_length_ms": 105000,
        "prompt": (
            "Dancehall, 98 BPM, female chant-style hook in patois, riddim hook plays solo for "
            "the first 6 seconds, punchy horn stabs, energetic party mood, single verse only, "
            "double chorus to close, runtime 1:45, polished commercial dancehall mix."
        ),
    },
    {
        "id": "08",
        "title": "GLC Radio - Amapiano-Zouk",
        "genre": "amapiano-zouk",
        "vocal": "female",
        "music_length_ms": 110000,
        "prompt": (
            "Amapiano rhythm section fused with zouk melodic sensibility, 108 BPM, "
            "breathy female French and English vocal hook, log drum plus zouk guitar arpeggios, "
            "airy piano stabs, hook from second 5, no slow build, runtime 1:50, "
            "novel crossover radio mix."
        ),
    },
]

# Requested next mixed set. Skip remakes of Modern Zouk-Love and 8-Bar Blitz Rap (already on disk).
BATCH_2 = [
    {
        "id": "09",
        "title": "GLC Radio - Electro Club",
        "genre": "electro-club",
        "vocal": "male",
        "music_length_ms": 110000,
        "prompt": (
            "Peak-time electro club music, 128 BPM, male vocal chops as a rhythmic hook, "
            "four-on-the-floor club kick, driving bassline, dark warehouse synth stabs, "
            "no ballad, no pop verse, drop in the first 8 seconds, chorus hook repeats, "
            "runtime 1:50, festival club mix scaled for radio."
        ),
    },
    {
        "id": "10",
        "title": "GLC Radio - Roots Reggae",
        "genre": "reggae",
        "vocal": "female",
        "music_length_ms": 110000,
        "prompt": (
            "Classic reggae, 78 BPM, female lead vocalist, one-drop drum pattern, "
            "offbeat skank guitar, warm bubbling bass, organ bubble, radio-clean uplifting hook "
            "in the first 10 seconds, chorus repeats twice, no dancehall, no trap, "
            "runtime 1:50, sunny Caribbean radio mix."
        ),
    },
    {
        "id": "11",
        "title": "GLC Radio - Pure Afrobeats",
        "genre": "afrobeats",
        "vocal": "female",
        "music_length_ms": 110000,
        "prompt": (
            "Pure classic Afrobeats, 105 BPM, female lead vocalist, log drums and shekere only, "
            "no amapiano piano, no highlife guitar fusion, no zouk, no electro, "
            "smooth dance-ready groove, English and Pidgin call-and-response chorus, "
            "hook in the first 8 seconds, no bridge, runtime 1:50, festival-ready polish."
        ),
    },
]


def load_api_key() -> str:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        raise SystemExit("Missing .env")
    for line in env_path.read_text().splitlines():
        if line.startswith("ELEVENLABS_API_KEY=") and not line.strip().startswith("#"):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise SystemExit("ELEVENLABS_API_KEY is empty in .env")


def playlist_lines() -> list[str]:
    if not PLAYLIST.is_file():
        return []
    return [line.strip() for line in PLAYLIST.read_text().splitlines() if line.strip()]


def append_playlist(filename: str) -> None:
    line = f"{LIQ_PREFIX}{filename}"
    existing = PLAYLIST.read_text() if PLAYLIST.is_file() else ""
    lines = [row.strip() for row in existing.splitlines() if row.strip()]
    if line in lines:
        return
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    with PLAYLIST.open("a") as handle:
        handle.write(f"{prefix}{line}\n")


def compose(api_key: str, prompt: str, music_length_ms: int) -> bytes:
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "prompt": prompt,
        "music_length_ms": music_length_ms,
        "model_id": MODEL_ID,
        "force_instrumental": False,
    }
    response = requests.post(
        COMPOSE_URL,
        headers=headers,
        json=payload,
        params={"output_format": "mp3_44100_128"},
        timeout=180,
    )
    content_type = response.headers.get("content-type", "")
    if response.status_code == 200 and len(response.content) > 1000 and (
        content_type.startswith("audio/")
        or response.content[:3] == b"ID3"
        or response.content[:2] == b"\xff\xfb"
    ):
        return response.content

    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text[:400]}

    detail = body.get("detail") if isinstance(body, dict) else None
    status = ""
    suggestion = ""
    if isinstance(detail, dict):
        status = str(detail.get("status") or "")
        data = detail.get("data") or {}
        if isinstance(data, dict):
            suggestion = str(data.get("prompt_suggestion") or "")
    if status == "bad_prompt" and suggestion:
        print(f"  bad_prompt, retrying with official suggestion")
        return compose(api_key, suggestion, music_length_ms)

    raise RuntimeError(f"HTTP {response.status_code}: {body}")


BATCHES = {"1": BATCH_1, "2": BATCH_2}


def main() -> int:
    batch_id = sys.argv[1] if len(sys.argv) > 1 else "1"
    batch = BATCHES.get(batch_id)
    if not batch:
        raise SystemExit(f"Unknown batch {batch_id!r}. Use: {' '.join(BATCHES)}")
    api_key = load_api_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for item in batch:
        filename = f"{item['title']}.mp3"
        dest = OUT_DIR / filename
        prompt = f"{UNIVERSAL} {item['vocal']} lead. {item['prompt']}"
        print(f"[{item['id']}] {item['genre']} / {item['vocal']} — {item['title']}")
        try:
            audio = compose(api_key, prompt, item["music_length_ms"])
            dest.write_bytes(audio)
            append_playlist(filename)
            print(f"  saved {dest.name} ({len(audio)} bytes)")
            results.append({"title": item["title"], "genre": item["genre"], "ok": True, "bytes": len(audio)})
        except Exception as exc:
            print(f"  FAILED: {exc}")
            results.append({"title": item["title"], "genre": item["genre"], "ok": False, "error": str(exc)})
            # Billing/auth failures should stop the batch.
            err = str(exc).lower()
            if any(token in err for token in ("402", "401", "insufficient", "quota", "payment")):
                print("Stopping batch after billing or auth error.")
                break
        time.sleep(2)

    summary = OUT_DIR / f"glc_radio_batch{batch_id}.json"
    summary.write_text(json.dumps(results, indent=2))
    ok = sum(1 for row in results if row.get("ok"))
    print(f"Done. {ok}/{len(results)} tracks written.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
