"""HeyGen REST v3 client for complementary GRO News video bulletins.

Audio remains the source of truth. This module is only invoked after a successful
broadcast, from POST /routes2/news/video/<task_id>. Video failures never change
the news task status.
"""

from __future__ import annotations

import json
import os
import threading
import time

import requests

HEYGEN_API_BASE = "https://api.heygen.com"
ANCHOR_AVATAR_ID = "5223f29b020245e990dcb548735f8b7c"
ANCHOR_VOICE_ID = "d7f9bb599ac24919abf13bb43c90f055"
ANCHOR_NAME = "GRO News Anchor"

_LOOK_POLL_SECONDS = 10
_LOOK_TIMEOUT_SECONDS = 300
_VIDEO_POLL_SECONDS = 10
_VIDEO_TIMEOUT_SECONDS = 900
_REQUEST_TIMEOUT = (10, 60)

_roster_lock = threading.Lock()

_REPORTER_PROMPTS = {
    "sports": {
        "name": "Ernest",
        "avatar_name": "GRO News Ernest",
        "look_prompt": (
            "Ghanaian man in his early 30s, athletic build, short cropped black hair, "
            "warm brown skin, confident smile, wearing a navy sports-desk blazer over "
            "a collared shirt, standing in a modern Accra newsroom with LED screens "
            "showing stadium lights, professional broadcast lighting"
        ),
        "voice_prompt": (
            "Warm, energetic West African English male sports reporter, mid-30s, "
            "clear diction, lively but professional for a radio-to-TV bulletin"
        ),
        "gender": "male",
    },
    "finance": {
        "name": "Isabella",
        "avatar_name": "GRO News Isabella",
        "look_prompt": (
            "West African woman in her 30s, polished professional look, dark hair "
            "pulled back, wearing a charcoal tailored blazer, standing at a finance "
            "desk in a contemporary Accra newsroom with market tickers softly out of "
            "focus, warm studio lighting"
        ),
        "voice_prompt": (
            "Clear, measured West African English female finance reporter, 30s, "
            "authoritative but approachable, moderate pace"
        ),
        "gender": "female",
    },
    "tech": {
        "name": "Mark",
        "avatar_name": "GRO News Mark",
        "look_prompt": (
            "British-Ghanaian man in his 30s, short neat hair, glasses, wearing a "
            "smart casual blazer over a dark shirt, standing in a modern tech news "
            "alcove with soft blue LED lighting and screens, professional broadcast look"
        ),
        "voice_prompt": (
            "British English male technology reporter, 30s, clear and curious, "
            "slightly conversational but still news-desk professional"
        ),
        "gender": "male",
    },
    "politics": {
        "name": "Edith",
        "avatar_name": "GRO News Edith",
        "look_prompt": (
            "Ghanaian woman in her late 30s, composed expression, natural dark hair, "
            "wearing a deep green structured jacket, standing in a parliamentary "
            "newsroom set with muted wood panels and a Ghana flag softly in the "
            "background, cinematic studio lighting"
        ),
        "voice_prompt": (
            "Calm, precise West African English female politics correspondent, "
            "late 30s, measured pace, serious but not stiff"
        ),
        "gender": "female",
    },
    "health": {
        "name": "Clara",
        "avatar_name": "GRO News Clara",
        "look_prompt": (
            "West African woman in her 30s, warm open expression, natural hair, "
            "wearing a light blue professional blouse, standing in a clean health "
            "desk set with soft daylight and a blurred clinic graphic, broadcast lighting"
        ),
        "voice_prompt": (
            "Warm, reassuring West African English female health reporter, 30s, "
            "clear diction, unhurried and trustworthy"
        ),
        "gender": "female",
    },
    "news": {
        "name": "James",
        "avatar_name": "GRO News James",
        "look_prompt": (
            "Ghanaian man in his 40s, short hair, neat beard, wearing a navy newsroom "
            "blazer and open-collar shirt, standing in a general assignment news set "
            "with Accra skyline graphics, professional warm lighting"
        ),
        "voice_prompt": (
            "Steady West African English male general-assignment reporter, 40s, "
            "neutral news cadence, clear and grounded"
        ),
        "gender": "male",
    },
}


def _log(event: str, **fields) -> None:
    payload = {"stage": event, **fields}
    print("PIPELINE " + json.dumps(payload, default=str))
    extras = " ".join(f"{key}={value!r}" for key, value in fields.items())
    print(f"{event} {extras}".strip())


def heygen_api_key() -> str:
    return (os.getenv("HEYGEN_API_KEY") or "").strip()


def _headers(api_key: str) -> dict:
    return {
        "X-Api-Key": api_key,
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _unwrap(payload):
    if isinstance(payload, dict) and "data" in payload and payload["data"] is not None:
        return payload["data"]
    return payload


def _error_message(payload, fallback: str) -> str:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("code") or fallback)
        if isinstance(err, str) and err.strip():
            return err
        if payload.get("message"):
            return str(payload["message"])
        if payload.get("failure_message"):
            return str(payload["failure_message"])
    return fallback


def _heygen_request(method: str, path: str, api_key: str, json_body=None):
    url = f"{HEYGEN_API_BASE}{path}"
    response = requests.request(
        method,
        url,
        headers=_headers(api_key),
        json=json_body,
        timeout=_REQUEST_TIMEOUT,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text[:400]}
    if response.status_code >= 400:
        raise RuntimeError(
            f"HeyGen {method} {path} HTTP {response.status_code}: "
            f"{_error_message(payload, response.text[:240])}"
        )
    return _unwrap(payload)


def _is_anchor_identity(avatar_id: str, voice_id: str) -> bool:
    return avatar_id == ANCHOR_AVATAR_ID or voice_id == ANCHOR_VOICE_ID


def _create_prompt_avatar(api_key: str, name: str, prompt: str) -> str:
    data = _heygen_request(
        "POST",
        "/v3/avatars",
        api_key,
        {"type": "prompt", "name": name, "prompt": prompt[:1000]},
    )
    look = {}
    if isinstance(data, dict):
        look = data.get("avatar_item") or data
    avatar_id = (
        (look.get("id") if isinstance(look, dict) else None)
        or (data.get("avatar_id") if isinstance(data, dict) else None)
        or (data.get("id") if isinstance(data, dict) else None)
    )
    if not avatar_id:
        raise RuntimeError(f"HeyGen avatar create returned no look id: {data!r}"[:400])
    return str(avatar_id)


def _poll_look(api_key: str, avatar_id: str) -> str:
    deadline = time.time() + _LOOK_TIMEOUT_SECONDS
    last_status = "unknown"
    last_error = None
    while time.time() < deadline:
        look = {}
        for path in (f"/v3/avatars/looks/{avatar_id}", f"/v3/avatars/{avatar_id}"):
            try:
                data = _heygen_request("GET", path, api_key)
                look = data.get("avatar_item") if isinstance(data, dict) and "avatar_item" in data else data
                if not isinstance(look, dict):
                    look = data if isinstance(data, dict) else {}
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                look = {}
        last_status = str((look or {}).get("status") or "unknown").lower()
        _log("heygen_poll", resource="look", avatar_id=avatar_id, status=last_status)
        if last_status in {"completed", "complete", "ready", "success"}:
            return avatar_id
        if last_status in {"failed", "rejected", "error"}:
            raise RuntimeError(f"HeyGen look {avatar_id} failed with status={last_status}")
        time.sleep(_LOOK_POLL_SECONDS)
    if last_error:
        raise TimeoutError(
            f"HeyGen look {avatar_id} not ready after {_LOOK_TIMEOUT_SECONDS}s "
            f"(last={last_status}, error={last_error})"
        )
    raise TimeoutError(f"HeyGen look {avatar_id} not ready after {_LOOK_TIMEOUT_SECONDS}s (last={last_status})")


def _design_voice(api_key: str, prompt: str, gender: str) -> str:
    data = _heygen_request(
        "POST",
        "/v3/voices",
        api_key,
        {"prompt": prompt[:1000], "gender": gender, "locale": "en-US"},
    )
    voices = []
    if isinstance(data, dict):
        voices = data.get("voices") or []
        if not voices and data.get("voice_id"):
            voices = [data]
    for voice in voices:
        if not isinstance(voice, dict):
            continue
        voice_id = voice.get("voice_id") or voice.get("id")
        if voice_id and str(voice_id) != ANCHOR_VOICE_ID:
            return str(voice_id)
    raise RuntimeError("HeyGen voice design returned no usable voice_id")


def ensure_reporter_identity(desk: str, reporter_name: str, api_key: str) -> dict:
    """Return {avatar_id, voice_id} for a desk, creating once and reusing later."""
    from glconnect.models import NewsHeygenRoster, db

    prompts = _REPORTER_PROMPTS.get(desk) or _REPORTER_PROMPTS["news"]
    with _roster_lock:
        row = NewsHeygenRoster.query.filter_by(desk=desk).first()
        if row and row.avatar_id and row.voice_id and row.status == "ready":
            if _is_anchor_identity(row.avatar_id, row.voice_id):
                _log(
                    "heygen_anchor_guard",
                    desk=desk,
                    reason="stored_ids_match_anchor",
                )
                row.status = "failed"
                row.last_error = "Stored reporter IDs collided with the studio anchor"
                db.session.commit()
            else:
                _log(
                    "heygen_roster",
                    desk=desk,
                    name=reporter_name,
                    status="reuse",
                    avatar_id=row.avatar_id,
                    voice_id=row.voice_id,
                )
                return {"avatar_id": row.avatar_id, "voice_id": row.voice_id, "name": row.reporter_name}

        if row is None:
            row = NewsHeygenRoster(
                desk=desk,
                reporter_name=reporter_name or prompts["name"],
                status="pending",
            )
            db.session.add(row)
            db.session.commit()

        try:
            if not row.avatar_id:
                row.avatar_id = _create_prompt_avatar(
                    api_key, prompts["avatar_name"], prompts["look_prompt"]
                )
                row.status = "pending"
                db.session.commit()
                _log("heygen_create", resource="avatar", desk=desk, avatar_id=row.avatar_id)
            _poll_look(api_key, row.avatar_id)

            if not row.voice_id:
                row.voice_id = _design_voice(api_key, prompts["voice_prompt"], prompts["gender"])
                db.session.commit()
                _log("heygen_create", resource="voice", desk=desk, voice_id=row.voice_id)

            if _is_anchor_identity(row.avatar_id, row.voice_id):
                _log("heygen_anchor_guard", desk=desk, reason="created_ids_match_anchor")
                row.status = "failed"
                row.last_error = "Reporter identity collided with studio anchor IDs"
                row.avatar_id = None
                row.voice_id = None
                db.session.commit()
                raise RuntimeError(row.last_error)

            row.status = "ready"
            row.last_error = None
            row.reporter_name = reporter_name or row.reporter_name
            db.session.commit()
            _log(
                "heygen_roster",
                desk=desk,
                name=row.reporter_name,
                status="ready",
                avatar_id=row.avatar_id,
                voice_id=row.voice_id,
            )
            return {"avatar_id": row.avatar_id, "voice_id": row.voice_id, "name": row.reporter_name}
        except Exception as exc:
            row.status = "failed"
            row.last_error = str(exc)[:1000]
            db.session.commit()
            _log("heygen_clip_fail", desk=desk, resource="roster", error=str(exc)[:240])
            raise


def _create_avatar_video(api_key: str, avatar_id: str, voice_id: str, script: str, title: str) -> str:
    data = _heygen_request(
        "POST",
        "/v3/videos",
        api_key,
        {
            "type": "avatar",
            "avatar_id": avatar_id,
            "voice_id": voice_id,
            "script": script,
            "title": title[:120],
            "resolution": "720p",
            "aspect_ratio": "16:9",
        },
    )
    video_id = None
    if isinstance(data, dict):
        video_id = data.get("video_id") or data.get("id")
        if not video_id and isinstance(data.get("video"), dict):
            video_id = data["video"].get("id") or data["video"].get("video_id")
    if not video_id:
        raise RuntimeError(f"HeyGen video create returned no video_id: {data!r}"[:400])
    _log("heygen_create", resource="video", video_id=video_id, title=title)
    return str(video_id)


def _poll_video(api_key: str, video_id: str) -> dict:
    deadline = time.time() + _VIDEO_TIMEOUT_SECONDS
    last_status = "unknown"
    while time.time() < deadline:
        data = _heygen_request("GET", f"/v3/videos/{video_id}", api_key)
        if not isinstance(data, dict):
            data = {}
        last_status = str(data.get("status") or "unknown").lower()
        _log("heygen_poll", resource="video", video_id=video_id, status=last_status)
        if last_status in {"completed", "complete", "success"}:
            url = data.get("video_url") or data.get("url")
            if not url:
                raise RuntimeError(f"HeyGen video {video_id} completed without video_url")
            return {
                "video_id": video_id,
                "url": url,
                "duration": data.get("duration"),
                "thumbnail_url": data.get("thumbnail_url"),
            }
        if last_status in {"failed", "error"}:
            raise RuntimeError(
                data.get("failure_message")
                or data.get("error")
                or f"HeyGen video {video_id} failed"
            )
        time.sleep(_VIDEO_POLL_SECONDS)
    raise TimeoutError(f"HeyGen video {video_id} not ready after {_VIDEO_TIMEOUT_SECONDS}s (last={last_status})")


def _clip_record(**fields) -> dict:
    clip = {
        "role": fields.get("role"),
        "desk": fields.get("desk"),
        "name": fields.get("name"),
        "topic": fields.get("topic"),
        "status": fields.get("status", "queued"),
        "video_id": fields.get("video_id"),
        "url": fields.get("url"),
        "error": fields.get("error"),
    }
    return clip


def _public_clip(clip: dict) -> dict:
    return {
        "role": clip.get("role"),
        "desk": clip.get("desk"),
        "name": clip.get("name"),
        "topic": clip.get("topic"),
        "status": clip.get("status"),
        "video_id": clip.get("video_id"),
        "url": clip.get("url"),
        "error": clip.get("error"),
    }


def generate_video_bulletin(task_id: str, scripts: dict, merge_result) -> dict:
    """Create HeyGen clips from saved scripts. merge_result(patch) persists heygen state."""
    warnings = []
    clips = []
    api_key = heygen_api_key()
    if not api_key:
        _log("heygen_skip", reason="no_api_key")
        state = {
            "status": "failed",
            "clips": [],
            "warnings": ["HeyGen API key is not set"],
        }
        merge_result({"heygen": state})
        return state

    intro = (scripts.get("intro") or "").strip()
    outro = (scripts.get("outro") or "").strip()
    reporters = scripts.get("reporters") or []
    _log(
        "heygen_scripts",
        intro_chars=len(intro),
        outro_chars=len(outro),
        reporters=len(reporters),
    )

    state = {"status": "processing", "clips": clips, "warnings": warnings}

    def persist():
        merge_result({
            "heygen": {
                "status": state["status"],
                "clips": [_public_clip(item) for item in clips],
                "warnings": warnings,
            }
        })

    persist()

    def render_clip(clip):
        try:
            if not (clip.get("script") or "").strip():
                raise RuntimeError("Empty script")
            if _is_anchor_identity(clip["avatar_id"], clip["voice_id"]) and clip["role"] not in (
                "anchor_intro",
                "anchor_outro",
            ):
                _log("heygen_anchor_guard", role=clip["role"], desk=clip.get("desk"))
                raise RuntimeError("Reporter clip blocked from using the studio anchor identity")
            video_id = _create_avatar_video(
                api_key,
                clip["avatar_id"],
                clip["voice_id"],
                clip["script"].strip(),
                clip["title"],
            )
            clip["video_id"] = video_id
            clip["status"] = "processing"
            persist()
            rendered = _poll_video(api_key, video_id)
            clip["status"] = "completed"
            clip["url"] = rendered["url"]
            clip["error"] = None
        except Exception as exc:
            clip["status"] = "failed"
            clip["error"] = str(exc)[:400]
            warnings.append(f"{clip['role']}: {clip['error']}")
            _log("heygen_clip_fail", role=clip["role"], desk=clip.get("desk"), error=clip["error"])
        persist()
        return clip

    def queue_and_render(clip):
        clips.append(clip)
        persist()
        return render_clip(clip)

    if intro:
        queue_and_render(
            _clip_record(
                role="anchor_intro",
                name=ANCHOR_NAME,
                status="queued",
            )
            | {
                "avatar_id": ANCHOR_AVATAR_ID,
                "voice_id": ANCHOR_VOICE_ID,
                "script": intro,
                "title": f"GRO News intro {task_id[:8]}",
            }
        )

    seen_desks = []
    for reporter in reporters:
        desk = reporter.get("desk") or "news"
        name = reporter.get("name") or desk
        topic = reporter.get("topic") or ""
        script = reporter.get("script") or ""
        try:
            identity = ensure_reporter_identity(desk, name, api_key)
        except Exception as exc:
            failed = _clip_record(
                role="reporter",
                desk=desk,
                name=name,
                topic=topic,
                status="failed",
                error=str(exc)[:400],
            )
            clips.append(failed)
            warnings.append(f"reporter {name}: {failed['error']}")
            persist()
            continue
        if desk not in seen_desks:
            seen_desks.append(desk)
        queue_and_render(
            _clip_record(
                role="reporter",
                desk=desk,
                name=identity.get("name") or name,
                topic=topic,
                status="queued",
            )
            | {
                "avatar_id": identity["avatar_id"],
                "voice_id": identity["voice_id"],
                "script": script,
                "title": f"GRO News {name} {task_id[:8]}",
            }
        )

    if outro:
        queue_and_render(
            _clip_record(
                role="anchor_outro",
                name=ANCHOR_NAME,
                status="queued",
            )
            | {
                "avatar_id": ANCHOR_AVATAR_ID,
                "voice_id": ANCHOR_VOICE_ID,
                "script": outro,
                "title": f"GRO News outro {task_id[:8]}",
            }
        )

    completed = [clip for clip in clips if clip.get("status") == "completed" and clip.get("url")]
    failed = [clip for clip in clips if clip.get("status") == "failed"]
    if completed and not failed:
        status = "completed"
    elif completed:
        status = "partial"
    else:
        status = "failed"
    state["status"] = status
    _log(
        "heygen_summary",
        status=status,
        completed=len(completed),
        failed=len(failed),
        desks=seen_desks,
    )
    persist()
    return {
        "status": status,
        "clips": [_public_clip(item) for item in clips],
        "warnings": warnings,
    }
