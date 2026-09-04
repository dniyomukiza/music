#!/usr/bin/env python3
"""
Search X only, write a short talk-show script, then send it to Grok Imagine
Video 1.5 as one presenter clip. Stdout is the video path.

Prefers XAI_API_KEY from .env, then GROK_API, then GROK_API_KEY.

Examples:
  python3 scripts/test_grok_api.py
  python3 scripts/test_grok_api.py --topic "your topic"
  python3 scripts/test_grok_api.py --voice helix --output video/grok_host/show.mp4
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
XAI_BASE = "https://api.x.ai/v1"
XAI_TTS_URL = f"{XAI_BASE}/tts"
XAI_IMAGE_URL = f"{XAI_BASE}/images/generations"
XAI_VIDEO_URL = f"{XAI_BASE}/videos/generations"
DEFAULT_MODEL = os.getenv("GROK_MODEL", "grok-4.6")
DEFAULT_HOST_VOICE = os.getenv("GROK_HOST_VOICE", "helix")
DEFAULT_IMAGE_MODEL = os.getenv("GROK_IMAGE_MODEL", "grok-imagine-image-2.0")
DEFAULT_VIDEO_MODEL = os.getenv("GROK_VIDEO_MODEL", "grok-imagine-video-1.5")
MAX_X_HANDLES = 20
MAX_TTS_CHARS = 15000
MAX_VIDEO_SECONDS = 15
WORDS_PER_SECOND = 2.4
HOST_AUDIO_DIR = ROOT / "video" / "grok_host"
GLC_SET = (
    "GLC Media branding is always visible in the background: a dark void studio "
    "with bronze-gold GLC MEDIA wordmark lighting on the back wall or frosted "
    "glass, subtle bronze edge light, no other network names. The mark stays "
    "behind the host, readable but not covering the face. No random watermarks "
    "or captions."
)
HOST_LOOK = (
    "Photorealistic late-night talk-show host at a desk in a small GLC Media TV "
    "studio, warm key light, microphone on the desk, looking into camera, 16:9. "
    f"{GLC_SET}"
)

SCRIPT_JSON_SCHEMA = """
Return ONLY valid JSON, with no Markdown fence, using this exact shape:
{
  "reports": [
    {
      "topic": "<exact searched topic>",
      "script": "<spoken talk-show script for one host to read aloud>"
    }
  ]
}
Write one report for every topic, in the same order.

This is a talk-show segment, not a wire summary and not a news bulletin.
One host talks the whole time. Write words that person can read on camera.
No titles, no headlines, no asterisks, no bullet lists, no stage directions,
no "Voices on X" appendix, no URLs.

Search X only. Do not use the web. Open like a live host, name the topic,
then include up to 2 real X posts or comments found with x_search. Prefer
one supportive and one critical post when both exist. If you only find one
side, use that one or two posts and do not invent the other. Attribute each
by name or @handle, then a short quote or tight paraphrase. Do not invent
handles, quotes, numbers, or posts. If X is thin, keep the host talking and
skip fake guests.

Keep it conversational and balanced. The host should not take a side. End
with a short close. Keep the whole script short enough for one 15-second
Imagine clip: about 4 to 6 spoken sentences.
""".strip()


def resolve_api_key() -> tuple[str | None, str | None]:
    for name in ("XAI_API_KEY", "GROK_API", "GROK_API_KEY"):
        value = (os.getenv(name) or "").strip()
        if value:
            return value, name
    return None, None


def mask_key(key: str) -> str:
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}…{key[-4:]}"


def parse_handles(value: str | None) -> list[str]:
    handles: list[str] = []
    for raw in (value or "").split(","):
        handle = raw.strip().lstrip("@")
        if handle and handle not in handles:
            handles.append(handle)
    if len(handles) > MAX_X_HANDLES:
        raise ValueError(f"At most {MAX_X_HANDLES} X handles are allowed")
    return handles


def parse_iso_date(value: str | None, option_name: str) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{option_name} must use YYYY-MM-DD") from exc


def parse_topics(topic_flags: list[str] | None, topics_csv: str | None) -> list[str]:
    topics: list[str] = []
    for value in topic_flags or []:
        topic = " ".join(value.split())
        if topic and topic not in topics:
            topics.append(topic)
    for raw in (topics_csv or "").split(","):
        topic = " ".join(raw.split())
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def prompt_topics() -> list[str]:
    """Ask for topics one at a time until the user is done."""
    print(
        "Enter topics to search, one per line. Empty line or 'done' to search.",
        file=sys.stderr,
    )
    topics: list[str] = []
    while True:
        try:
            raw = input(f"Topic {len(topics) + 1}: ")
        except EOFError:
            print("", file=sys.stderr)
            break
        except KeyboardInterrupt:
            print("\nCanceled.", file=sys.stderr)
            sys.exit(130)
        topic = " ".join(raw.split())
        if not topic or topic.lower() in {"done", "q", "quit"}:
            break
        if topic not in topics:
            topics.append(topic)
    if not topics:
        print("No topics entered.", file=sys.stderr)
        sys.exit(1)
    print(f"Searching {len(topics)} topic(s)...", file=sys.stderr)
    return topics


def build_tools(
    *,
    use_web: bool,
    use_x: bool,
    from_date: str | None = None,
    to_date: str | None = None,
    allowed_handles: list[str] | None = None,
    excluded_handles: list[str] | None = None,
    enable_image: bool = False,
    enable_video: bool = False,
) -> list[dict[str, Any]]:
    allowed_handles = allowed_handles or []
    excluded_handles = excluded_handles or []
    if allowed_handles and excluded_handles:
        raise ValueError("allowed_x_handles and excluded_x_handles cannot be used together")
    if not use_x and (
        from_date
        or to_date
        or allowed_handles
        or excluded_handles
        or enable_image
        or enable_video
    ):
        raise ValueError("X-specific filters cannot be used with --web-only")

    tools: list[dict[str, Any]] = []
    if use_web:
        tools.append({"type": "web_search"})
    if use_x:
        x_tool: dict[str, Any] = {"type": "x_search"}
        if from_date:
            x_tool["from_date"] = from_date
        if to_date:
            x_tool["to_date"] = to_date
        if allowed_handles:
            x_tool["allowed_x_handles"] = allowed_handles
        if excluded_handles:
            x_tool["excluded_x_handles"] = excluded_handles
        if enable_image:
            x_tool["enable_image_understanding"] = True
        if enable_video:
            x_tool["enable_video_understanding"] = True
        tools.append(x_tool)
    if not tools:
        raise ValueError("At least one search tool must be enabled")
    return tools


def build_script_prompt(topics: list[str]) -> str:
    listed = json.dumps(topics)
    return (
        "Search each topic on X only. Do not use web search. Then write a short "
        "talk-show script for one presenter. Include up to two real X posts.\n"
        f"Topics: {listed}\n\n"
        f"{SCRIPT_JSON_SCHEMA}"
    )


def search_topics_for_scripts(
    api_key: str,
    topics: list[str],
    *,
    model: str = DEFAULT_MODEL,
    use_web: bool = False,
    use_x: bool = True,
    from_date: str | None = None,
    to_date: str | None = None,
    allowed_handles: list[str] | None = None,
    excluded_handles: list[str] | None = None,
    enable_image: bool = False,
    enable_video: bool = False,
    max_output_tokens: int = 4096,
) -> dict[str, Any]:
    """Search topics and return a news script summary for each."""
    tools = build_tools(
        use_web=use_web,
        use_x=use_x,
        from_date=from_date,
        to_date=to_date,
        allowed_handles=allowed_handles,
        excluded_handles=excluded_handles,
        enable_image=enable_image,
        enable_video=enable_video,
    )
    response = requests.post(
        f"{XAI_BASE}/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": build_script_prompt(topics),
                }
            ],
            "tools": tools,
            "max_output_tokens": max_output_tokens,
        },
        timeout=240,
    )
    if not response.ok:
        raise RuntimeError(
            f"Grok search failed ({response.status_code}): {_response_error(response)}"
        )

    raw = response.json()
    text = extract_response_text(raw)
    payload = parse_json_from_text(text) or {}
    reports = normalize_reports(topics, payload, text)
    return {
        "topics": topics,
        "model": model,
        "tools": tools,
        "reports": reports,
        "text": text,
        "citations": extract_citations(raw),
        "usage": raw.get("usage"),
        "response_id": raw.get("id"),
        "raw": raw,
    }


def spoken_scripts(result: dict[str, Any]) -> list[str]:
    return [
        " ".join(str(report.get("script") or "").split())
        for report in result.get("reports") or []
        if str(report.get("script") or "").strip()
    ]


def host_read_text(scripts: list[str]) -> str:
    return " [pause] ".join(scripts)


def topic_slug(topics: list[str]) -> str:
    first = re.sub(r"[^a-z0-9]+", "-", (topics[0] if topics else "show").lower())
    return first.strip("-")[:40] or "show"


def default_audio_path(topics: list[str]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return HOST_AUDIO_DIR / f"{topic_slug(topics)}-{stamp}.mp3"


def synthesize_host_audio(
    api_key: str,
    text: str,
    output_path: Path,
    *,
    voice_id: str = DEFAULT_HOST_VOICE,
    language: str = "en",
) -> Path:
    """Speak the host script with Grok TTS and write an MP3."""
    spoken = " ".join(text.split())
    if not spoken:
        raise ValueError("Host script is empty")
    if len(spoken) > MAX_TTS_CHARS:
        raise ValueError(f"Host script exceeds {MAX_TTS_CHARS} characters")

    response = requests.post(
        XAI_TTS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "text": spoken,
            "voice_id": voice_id,
            "language": language,
        },
        timeout=180,
    )
    if not response.ok:
        raise RuntimeError(
            f"Grok TTS failed ({response.status_code}): {_response_error(response)}"
        )
    content_type = (response.headers.get("Content-Type") or "").lower()
    body = response.content
    if "json" in content_type:
        raise RuntimeError(f"Grok TTS returned JSON instead of audio: {_response_error(response)}")
    if len(body) < 64:
        raise RuntimeError("Grok TTS returned empty audio")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(body)
    return output_path


def default_video_path(topics: list[str]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return HOST_AUDIO_DIR / f"{topic_slug(topics)}-{stamp}.mp4"


def split_script_scenes(text: str, *, max_words: int = 36, max_scenes: int = 1) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if max_scenes <= 1:
        return [cleaned]
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    if not sentences:
        return []
    scenes: list[str] = []
    current: list[str] = []
    words = 0
    for sentence in sentences:
        count = len(sentence.split())
        if current and words + count > max_words:
            scenes.append(" ".join(current))
            current = [sentence]
            words = count
            if len(scenes) >= max_scenes:
                return scenes
            continue
        current.append(sentence)
        words += count
    if current and len(scenes) < max_scenes:
        scenes.append(" ".join(current))
    return scenes


def scene_duration_seconds(text: str) -> int:
    words = max(1, len(text.split()))
    return max(6, min(MAX_VIDEO_SECONDS, round(words / WORDS_PER_SECOND)))


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def generate_host_still(api_key: str, *, model: str = DEFAULT_IMAGE_MODEL) -> str | None:
    """Return a temporary host image URL, or None if image generation is unavailable."""
    response = requests.post(
        XAI_IMAGE_URL,
        headers=_auth_headers(api_key),
        json={
            "model": model,
            "prompt": HOST_LOOK,
            "n": 1,
            "aspect_ratio": "16:9",
        },
        timeout=120,
    )
    if not response.ok:
        print(
            f"Host still skipped ({response.status_code}): {_response_error(response)}",
            file=sys.stderr,
        )
        return None
    data = response.json()
    items = data.get("data") or []
    if items and isinstance(items[0], dict):
        url = str(items[0].get("url") or "").strip()
        if url:
            return url
    return None


def start_imagine_video(
    api_key: str,
    prompt: str,
    *,
    duration: int,
    voice_id: str,
    host_image_url: str | None,
    resolution: str = "720p",
    model: str = DEFAULT_VIDEO_MODEL,
) -> str:
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "16:9",
        "resolution": resolution,
        "reference_audios": [{"voice_id": voice_id}],
    }
    if host_image_url:
        body["reference_images"] = [{"url": host_image_url}]
    response = requests.post(
        XAI_VIDEO_URL,
        headers=_auth_headers(api_key),
        json=body,
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(
            f"Imagine video failed ({response.status_code}): {_response_error(response)}"
        )
    request_id = str((response.json() or {}).get("request_id") or "").strip()
    if not request_id:
        raise RuntimeError("Imagine video returned no request_id")
    return request_id


def poll_imagine_video(
    api_key: str,
    request_id: str,
    *,
    timeout_seconds: int = 720,
    interval_seconds: int = 5,
) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = requests.get(
            f"{XAI_BASE}/videos/{request_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if not response.ok:
            raise RuntimeError(
                f"Imagine poll failed ({response.status_code}): {_response_error(response)}"
            )
        data = response.json() or {}
        status = str(data.get("status") or "").lower()
        if status == "done":
            url = str((data.get("video") or {}).get("url") or "").strip()
            if not url:
                raise RuntimeError("Imagine video finished without a URL")
            return url
        if status in {"failed", "expired"}:
            error = data.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else status
            raise RuntimeError(f"Imagine video {status}: {message}")
        time.sleep(interval_seconds)
    raise RuntimeError("Imagine video timed out")


def download_binary(url: str, output_path: Path) -> Path:
    response = requests.get(url, timeout=180)
    if not response.ok:
        raise RuntimeError(f"Download failed ({response.status_code}) for {url}")
    if len(response.content) < 64:
        raise RuntimeError("Downloaded file was empty")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def stitch_videos(clips: list[Path], output_path: Path) -> Path:
    if len(clips) == 1:
        if clips[0].resolve() != output_path.resolve():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(clips[0].read_bytes())
        return output_path
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg not found; keeping the first Imagine clip.", file=sys.stderr)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(clips[0].read_bytes())
        return output_path
    listing = output_path.with_suffix(".concat.txt")
    listing.write_text(
        "".join(f"file '{clip.resolve()}'\n" for clip in clips),
        encoding="utf-8",
    )
    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listing),
        "-c",
        "copy",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        command[-3:] = ["-c:v", "libx264", "-c:a", "aac", str(output_path)]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr[-800:] or "ffmpeg stitch failed")
    listing.unlink(missing_ok=True)
    return output_path


def scene_video_prompt(dialogue: str, *, has_image: bool) -> str:
    who = "The host from <IMAGE_1>" if has_image else "A late-night talk-show host at a desk"
    return (
        f"{who} speaks to camera with the voice from <AUDIO_0> on a GLC Media talk-show set. "
        f"{GLC_SET} "
        "Natural gestures, looking at camera, no captions and no lower-thirds. "
        f"They say exactly: {dialogue}"
    )


def generate_talkshow_video(
    api_key: str,
    script: str,
    output_path: Path,
    *,
    voice_id: str,
    max_scenes: int = 1,
    resolution: str = "720p",
    skip_host_image: bool = False,
) -> Path:
    scenes = split_script_scenes(script, max_scenes=max_scenes)
    if not scenes:
        raise ValueError("No talk-show scenes to render")
    host_image_url = None if skip_host_image else generate_host_still(api_key)
    clip_dir = output_path.parent / f"{output_path.stem}-clips"
    clips: list[Path] = []
    for index, scene in enumerate(scenes, 1):
        print(f"Imagine clip {index}/{len(scenes)} ({scene_duration_seconds(scene)}s)...", file=sys.stderr)
        request_id = start_imagine_video(
            api_key,
            scene_video_prompt(scene, has_image=bool(host_image_url)),
            duration=scene_duration_seconds(scene),
            voice_id=voice_id,
            host_image_url=host_image_url,
            resolution=resolution,
        )
        url = poll_imagine_video(api_key, request_id)
        clip_path = clip_dir / f"scene-{index:02d}.mp4"
        download_binary(url, clip_path)
        clips.append(clip_path)
    return stitch_videos(clips, output_path)


def normalize_reports(
    topics: list[str],
    payload: dict[str, Any],
    fallback_text: str,
) -> list[dict[str, Any]]:
    by_topic: dict[str, dict[str, Any]] = {}
    for item in payload.get("reports") or []:
        if not isinstance(item, dict):
            continue
        topic = " ".join(str(item.get("topic") or "").split())
        script = " ".join(str(item.get("script") or "").split())
        if not topic or not script:
            continue
        by_topic[topic.lower()] = {"topic": topic, "script": script}

    reports: list[dict[str, Any]] = []
    for topic in topics:
        match = by_topic.get(topic.lower())
        if match:
            reports.append({**match, "topic": topic})
            continue
        reports.append(
            {
                "topic": topic,
                "script": fallback_text.strip() if len(topics) == 1 else "",
            }
        )
    return reports


def extract_response_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "output_text":
                continue
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    if parts:
        return "\n".join(parts)

    for choice in data.get("choices") or []:
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    return "\n".join(parts)


def extract_citations(data: dict[str, Any]) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_citation(value: Any) -> None:
        if isinstance(value, str):
            url = value.strip()
            title = ""
        elif isinstance(value, dict):
            nested = value.get("url_citation")
            if isinstance(nested, dict):
                value = nested
            url = str(value.get("url") or value.get("uri") or "").strip()
            title = str(value.get("title") or "").strip()
        else:
            return
        if not url or url in seen:
            return
        seen.add(url)
        citations.append({"url": url, "title": title})

    for citation in data.get("citations") or []:
        add_citation(citation)
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for citation in item.get("citations") or []:
            add_citation(citation)
        for block in item.get("content") or []:
            if not isinstance(block, dict):
                continue
            for citation in block.get("citations") or []:
                add_citation(citation)
            for annotation in block.get("annotations") or []:
                add_citation(annotation)
    return citations


def parse_json_from_text(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def print_script_summaries(result: dict[str, Any], *, json_output: bool) -> None:
    scripts = spoken_scripts(result)
    if json_output:
        print(json.dumps({"scripts": scripts}, ensure_ascii=False))
        return
    print("\n\n".join(scripts))


def list_models(api_key: str) -> bool:
    print("1) GET /models", file=sys.stderr)
    try:
        response = requests.get(
            f"{XAI_BASE}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"   FAIL — network: {exc}", file=sys.stderr)
        return False
    if not response.ok:
        print(f"   FAIL ({response.status_code}) — {_response_error(response)}", file=sys.stderr)
        return False
    models = response.json().get("data") or []
    ids = [model.get("id", "?") for model in models[:8]]
    print(f"   OK ({response.status_code}) — sample models: {', '.join(ids)}", file=sys.stderr)
    return True


def run_ping(api_key: str, model: str) -> bool:
    print("\n2) POST /chat/completions (ping)", file=sys.stderr)
    try:
        response = requests.post(
            f"{XAI_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with exactly: GROK_OK"}],
                "max_tokens": 32,
                "temperature": 0,
            },
            timeout=60,
        )
    except requests.RequestException as exc:
        print(f"   FAIL — network: {exc}", file=sys.stderr)
        return False
    if not response.ok:
        print(f"   FAIL ({response.status_code}) — {_response_error(response)}", file=sys.stderr)
        return False
    data = response.json()
    content = (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    ).strip()
    print(f"   OK ({response.status_code}) Reply: {content[:200]}", file=sys.stderr)
    return "GROK_OK" in content.upper()


def _response_error(response: requests.Response) -> str:
    try:
        return json.dumps(response.json())[:1200]
    except ValueError:
        return response.text[:1200]


def _print_usage(usage: dict[str, Any] | None) -> None:
    if not usage:
        return
    print(
        "Usage:"
        f" input={usage.get('input_tokens', usage.get('prompt_tokens', '?'))},"
        f" output={usage.get('output_tokens', usage.get('completion_tokens', '?'))},"
        f" total={usage.get('total_tokens', '?')}",
        file=sys.stderr,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Search X, write a short presenter script, then make one Imagine 1.5 clip. "
            "With no --topic flags, prompts for topics until done."
        ),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model (default: {DEFAULT_MODEL})")
    parser.add_argument("--tools", action="store_true", help="Run a quick search-tools smoke test")
    parser.add_argument(
        "--topic",
        action="append",
        dest="topics_list",
        help="Topic to search. Repeat for multiple topics.",
    )
    parser.add_argument(
        "--topics",
        dest="topics_csv",
        help="Comma-separated topics to search",
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="Also ping models and chat before searching",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Print {\"video\": \"...\"} or {\"audio\": \"...\"}",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_HOST_VOICE,
        help=f"Grok host voice (default: {DEFAULT_HOST_VOICE})",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Talk-show MP4 path (default: video/grok_host/<topic>-<time>.mp4)",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Print the spoken script and skip audio and video",
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Write host MP3 and skip Imagine video",
    )
    parser.add_argument(
        "--max-scenes",
        type=int,
        default=1,
        help="Max 15-second Imagine clips (default: 1)",
    )
    parser.add_argument(
        "--resolution",
        default="720p",
        choices=("480p", "720p", "1080p"),
        help="Imagine video resolution (default: 720p)",
    )
    parser.add_argument(
        "--no-host-image",
        action="store_true",
        help="Skip the host still and use text-to-video only",
    )
    parser.add_argument("--save", metavar="FILE", help="Save the full raw API response to FILE")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print citations and token usage to stderr",
    )
    search_group = parser.add_mutually_exclusive_group()
    search_group.add_argument("--web-only", action="store_true", help="Use web_search only")
    search_group.add_argument(
        "--with-web",
        action="store_true",
        help="Also use web_search. Default is X search only.",
    )
    parser.add_argument("--from-date", help="X search start date (YYYY-MM-DD; default: today)")
    parser.add_argument("--to-date", help="X search end date (YYYY-MM-DD; default: today)")
    handles_group = parser.add_mutually_exclusive_group()
    handles_group.add_argument(
        "--allowed-handles",
        help="Comma-separated X handles to include (maximum 20)",
    )
    handles_group.add_argument(
        "--excluded-handles",
        help="Comma-separated X handles to exclude (maximum 20)",
    )
    parser.add_argument(
        "--enable-image",
        action="store_true",
        help="Let x_search analyze images in posts",
    )
    parser.add_argument(
        "--enable-video",
        action="store_true",
        help="Let x_search analyze videos in posts",
    )
    return parser


def main() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    topics = parse_topics(args.topics_list, args.topics_csv)

    if args.tools and topics:
        parser.error("--tools and --topic/--topics are separate modes; choose one")
    if not topics and not args.tools and not args.ping:
        if not sys.stdin.isatty():
            parser.error("pass --topic or --topics, or run in a terminal to enter topics")
        topics = prompt_topics()

    api_key, source = resolve_api_key()
    if not api_key:
        print(
            "ERROR: Set XAI_API_KEY, GROK_API, or GROK_API_KEY in .env.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.verbose or args.ping or args.tools:
        print(f"Using {source}={mask_key(api_key)}", file=sys.stderr)
        print(f"Model: {args.model}", file=sys.stderr)

    if args.ping:
        if not list_models(api_key) or not run_ping(api_key, args.model):
            sys.exit(1)
        if not topics and not args.tools:
            print("SUCCESS: Grok API key works.", file=sys.stderr)
            return

    use_web = bool(args.web_only or args.with_web)
    use_x = not args.web_only
    search_topics = topics or (["top US news headline today"] if args.tools else [])
    try:
        allowed_handles = parse_handles(args.allowed_handles)
        excluded_handles = parse_handles(args.excluded_handles)
        from_date = parse_iso_date(args.from_date, "--from-date")
        to_date = parse_iso_date(args.to_date, "--to-date")
        if use_x:
            from_date = from_date or date.today().isoformat()
            to_date = to_date or date.today().isoformat()
        if from_date and to_date and from_date > to_date:
            raise ValueError("--from-date cannot be later than --to-date")

        result = search_topics_for_scripts(
            api_key,
            search_topics,
            model=args.model,
            use_web=use_web,
            use_x=use_x,
            from_date=from_date,
            to_date=to_date,
            allowed_handles=allowed_handles,
            excluded_handles=excluded_handles,
            enable_image=args.enable_image,
            enable_video=args.enable_video,
            max_output_tokens=512 if args.tools else 4096,
        )
    except (ValueError, RuntimeError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.save:
        save_path = Path(args.save).expanduser()
        save_path.write_text(json.dumps(result["raw"], indent=2), encoding="utf-8")
        print(f"Saved raw response to {save_path}", file=sys.stderr)

    if args.verbose:
        citations = result["citations"]
        if citations:
            print(f"Citations ({len(citations)}):", file=sys.stderr)
            for index, citation in enumerate(citations, 1):
                title = f" — {citation['title']}" if citation.get("title") else ""
                print(f"{index}. {citation['url']}{title}", file=sys.stderr)
        _print_usage(result.get("usage"))

    if args.tools:
        print(result["text"][:1000] or "(empty response)")
        print("SUCCESS: Grok search tools work.", file=sys.stderr)
        return

    missing = [report["topic"] for report in result["reports"] if not report.get("script")]
    if missing:
        print(
            "ERROR: No talk-show script for: " + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(2)

    scripts = spoken_scripts(result)
    if args.text_only:
        print_script_summaries(result, json_output=args.json_output)
        return

    spoken = host_read_text(scripts)
    requested = Path(args.output).expanduser() if args.output else None
    video_path = requested.with_suffix(".mp4") if requested else default_video_path(search_topics)
    try:
        if args.audio_only:
            audio_path = requested.with_suffix(".mp3") if requested else default_audio_path(search_topics)
            synthesize_host_audio(
                api_key,
                spoken,
                audio_path,
                voice_id=args.voice,
            )
            resolved = str(audio_path.resolve())
            if args.json_output:
                print(json.dumps({"audio": resolved}, ensure_ascii=False))
                return
            print(resolved)
            return

        print("Sending script to Imagine 1.5 as one presenter clip...", file=sys.stderr)
        generate_talkshow_video(
            api_key,
            spoken,
            video_path,
            voice_id=args.voice,
            max_scenes=max(1, args.max_scenes),
            resolution=args.resolution,
            skip_host_image=args.no_host_image,
        )
    except (ValueError, RuntimeError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    resolved = str(video_path.resolve())
    if args.json_output:
        print(json.dumps({"video": resolved}, ensure_ascii=False))
        return
    print(resolved)


if __name__ == "__main__":
    main()
