"""HeyGen REST v3 client for complementary GRO News video bulletins.

Audio remains the source of truth. This module is only invoked after a successful
broadcast, from POST /routes2/news/video/<task_id>. Video failures never change
the news task status.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
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

LOOK_KEY = "glc-studio-v1"
_STUDIO_BACKGROUND = (
    "standing in the GLC Media television studio, identical branded set for every "
    "presenter: dark charcoal newsroom walls, bronze-gold rim lighting, a large "
    "rear wall graphic that clearly reads GLC MEDIA in gold sans-serif letters, "
    "subtle forest-green edge lights, soft out-of-focus LED panels, professional "
    "broadcast lighting, no other network logos"
)

_roster_lock = threading.Lock()

_REPORTER_PROMPTS = {
    "sports": {
        "name": "Ernest",
        "avatar_name": "GRO News Ernest",
        "look_prompt": (
            "Black man in his early 30s, dark brown skin, short cropped black hair, "
            "athletic build, confident smile, wearing a navy sports-desk blazer over "
            "a collared shirt, " + _STUDIO_BACKGROUND
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
            "White woman in her 30s, fair skin, light brown hair pulled back, "
            "polished professional look, wearing a charcoal tailored blazer, "
            + _STUDIO_BACKGROUND
        ),
        "voice_prompt": (
            "Clear, measured female finance reporter, 30s, "
            "authoritative but approachable, moderate pace"
        ),
        "gender": "female",
    },
    "tech": {
        "name": "Mark",
        "avatar_name": "GRO News Mark",
        "look_prompt": (
            "White man in his 30s, light skin, short neat brown hair, glasses, "
            "wearing a smart casual blazer over a dark shirt, " + _STUDIO_BACKGROUND
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
            "Black woman in her late 30s, dark brown skin, natural dark hair, "
            "composed expression, wearing a deep green structured jacket, "
            + _STUDIO_BACKGROUND
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
            "White woman in her 30s, fair skin, shoulder-length auburn hair, "
            "warm open expression, wearing a light blue professional blouse, "
            + _STUDIO_BACKGROUND
        ),
        "voice_prompt": (
            "Warm, reassuring female health reporter, 30s, "
            "clear diction, unhurried and trustworthy"
        ),
        "gender": "female",
    },
    "news": {
        "name": "James",
        "avatar_name": "GRO News James",
        "look_prompt": (
            "Black man in his 40s, dark brown skin, short hair, neat beard, "
            "wearing a navy newsroom blazer and open-collar shirt, "
            + _STUDIO_BACKGROUND
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


def _heygen_request(method: str, path: str, api_key: str, json_body=None, params=None, unwrap=True):
    url = f"{HEYGEN_API_BASE}{path}"
    kwargs = {
        "headers": _headers(api_key),
        "timeout": _REQUEST_TIMEOUT,
        "params": params,
    }
    if json_body is not None:
        kwargs["json"] = json_body
    response = requests.request(method, url, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text[:400]}
    if response.status_code >= 400:
        raise RuntimeError(
            f"HeyGen {method} {path} HTTP {response.status_code}: "
            f"{_error_message(payload, response.text[:240])}"
        )
    return _unwrap(payload) if unwrap else payload


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


_voice_catalog_cache = {"voices": None, "fetched_at": 0}
_VOICE_CACHE_TTL = 3600
_DESK_VOICE_SLOT = {
    "sports": 0,
    "tech": 1,
    "news": 2,
    "finance": 0,
    "politics": 1,
    "health": 2,
}


def _extract_voice_rows(payload) -> list:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("voices"), list):
        return [row for row in payload["voices"] if isinstance(row, dict)]
    inner = payload.get("data")
    if isinstance(inner, list):
        return [row for row in inner if isinstance(row, dict)]
    if isinstance(inner, dict) and isinstance(inner.get("voices"), list):
        return [row for row in inner["voices"] if isinstance(row, dict)]
    if payload.get("voice_id") or payload.get("id"):
        return [payload]
    return []


def _list_catalog_voices(api_key: str) -> list:
    cached = _voice_catalog_cache.get("voices")
    fetched_at = _voice_catalog_cache.get("fetched_at") or 0
    if cached and (time.time() - fetched_at) < _VOICE_CACHE_TTL:
        return cached

    voices = []
    source = None
    try:
        payload = _heygen_request("GET", "/v2/voices", api_key, unwrap=False)
        voices = _extract_voice_rows(payload)
        source = "v2"
    except Exception as exc:
        _log("heygen_skip", resource="voices_v2", error=str(exc)[:240])

    if not voices:
        collected = []
        token = None
        source = "v3"
        for _page in range(8):
            params = {"language": "English", "type": "public", "limit": 100}
            if token:
                params["token"] = token
            payload = _heygen_request("GET", "/v3/voices", api_key, params=params, unwrap=False)
            page_rows = _extract_voice_rows(payload)
            collected.extend(page_rows)
            if isinstance(payload, dict) and payload.get("has_more") and payload.get("next_token"):
                token = payload.get("next_token")
                continue
            break
        voices = collected

    _voice_catalog_cache["voices"] = voices
    _voice_catalog_cache["fetched_at"] = time.time()
    _log("heygen_roster", resource="voice_catalog", source=source, count=len(voices))
    return voices


def _voice_id_of(voice: dict) -> str:
    return str(voice.get("voice_id") or voice.get("id") or "").strip()


def _voice_matches_catalog(voice: dict, gender: str) -> bool:
    voice_id = _voice_id_of(voice)
    if not voice_id or voice_id == ANCHOR_VOICE_ID:
        return False
    language = str(voice.get("language") or "").strip().lower()
    if language and "english" not in language and language not in {"en", "en-us", "en-gb", "en-au"}:
        return False
    voice_gender = str(voice.get("gender") or "").strip().lower()
    return (not voice_gender) or voice_gender == str(gender or "").strip().lower()


def _taken_voice_ids() -> set:
    from glconnect.models import NewsHeygenRoster

    taken = {ANCHOR_VOICE_ID}
    for row in NewsHeygenRoster.query.filter(NewsHeygenRoster.voice_id.isnot(None)).all():
        taken.add(row.voice_id)
    return taken


def _pick_catalog_voice(api_key: str, gender: str, desk: str) -> str:
    """Pick a public English catalog voice_id. Do not use voice design."""
    voices = [
        voice for voice in _list_catalog_voices(api_key)
        if _voice_matches_catalog(voice, gender)
    ]
    if not voices:
        raise RuntimeError(f"HeyGen voice catalog returned no English {gender} voices")

    taken = _taken_voice_ids()
    available = [voice for voice in voices if _voice_id_of(voice) not in taken] or voices
    slot = _DESK_VOICE_SLOT.get(desk, 0) % len(available)
    chosen = available[slot]
    voice_id = _voice_id_of(chosen)
    _log(
        "heygen_create",
        resource="voice",
        source="catalog",
        desk=desk,
        gender=gender,
        name=chosen.get("name"),
        language=chosen.get("language"),
        voice_id=voice_id,
        candidates=len(available),
    )
    return voice_id


_look_key_column_ready = False


def _ensure_look_key_column(db) -> None:
    """Add look_key on older news_heygen_roster tables so diversity refreshes can run."""
    global _look_key_column_ready
    if _look_key_column_ready:
        return
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(db.engine)
        if "news_heygen_roster" not in inspector.get_table_names():
            _look_key_column_ready = True
            return
        columns = {col["name"] for col in inspector.get_columns("news_heygen_roster")}
        if "look_key" in columns:
            _look_key_column_ready = True
            return
        dialect = db.engine.dialect.name
        if dialect == "postgresql":
            db.session.execute(text(
                "ALTER TABLE news_heygen_roster ADD COLUMN IF NOT EXISTS look_key VARCHAR(64)"
            ))
        else:
            db.session.execute(text(
                "ALTER TABLE news_heygen_roster ADD COLUMN look_key VARCHAR(64)"
            ))
        db.session.commit()
        _look_key_column_ready = True
        _log("heygen_roster", resource="schema", status="added_look_key")
    except Exception as exc:
        db.session.rollback()
        _log("heygen_skip", resource="schema", error=str(exc)[:240])


def ensure_reporter_identity(desk: str, reporter_name: str, api_key: str) -> dict:
    """Reuse stored avatar_id + voice_id per desk. Create only what is still missing."""
    from glconnect.models import NewsHeygenRoster, db

    _ensure_look_key_column(db)
    prompts = _REPORTER_PROMPTS.get(desk) or _REPORTER_PROMPTS["news"]
    with _roster_lock:
        row = NewsHeygenRoster.query.filter_by(desk=desk).first()
        if row is None:
            row = NewsHeygenRoster(
                desk=desk,
                reporter_name=reporter_name or prompts["name"],
                status="pending",
                look_key=LOOK_KEY,
            )
            db.session.add(row)
            db.session.commit()

        stored_look = getattr(row, "look_key", None)
        if row.avatar_id and stored_look != LOOK_KEY:
            _log(
                "heygen_roster",
                desk=desk,
                status="refresh_look",
                previous_look=stored_look,
                look_key=LOOK_KEY,
            )
            row.avatar_id = None
            row.status = "pending"
            row.look_key = LOOK_KEY
            db.session.commit()

        def _reuse_if_complete():
            if not (row.avatar_id and row.voice_id):
                return None
            if getattr(row, "look_key", None) != LOOK_KEY:
                return None
            if _is_anchor_identity(row.avatar_id, row.voice_id):
                _log("heygen_anchor_guard", desk=desk, reason="stored_ids_match_anchor")
                row.status = "failed"
                row.last_error = "Stored reporter IDs collided with the studio anchor"
                row.avatar_id = None
                row.voice_id = None
                db.session.commit()
                return None
            if row.status != "ready":
                row.status = "ready"
                row.last_error = None
                row.reporter_name = reporter_name or row.reporter_name
                row.look_key = LOOK_KEY
                db.session.commit()
            _log(
                "heygen_roster",
                desk=desk,
                name=row.reporter_name,
                status="reuse",
                avatar_id=row.avatar_id,
                voice_id=row.voice_id,
            )
            return {"avatar_id": row.avatar_id, "voice_id": row.voice_id, "name": row.reporter_name}

        reused = _reuse_if_complete()
        if reused:
            return reused

        try:
            created_avatar = False
            if not row.avatar_id:
                row.avatar_id = _create_prompt_avatar(
                    api_key, prompts["avatar_name"], prompts["look_prompt"]
                )
                row.status = "pending"
                row.look_key = LOOK_KEY
                db.session.commit()
                created_avatar = True
                _log("heygen_create", resource="avatar", desk=desk, avatar_id=row.avatar_id)
            else:
                _log(
                    "heygen_roster",
                    resource="avatar",
                    desk=desk,
                    status="reuse",
                    avatar_id=row.avatar_id,
                )

            # Only poll HeyGen while a new look is still training.
            if created_avatar or row.status == "pending":
                _poll_look(api_key, row.avatar_id)

            if not row.voice_id:
                row.voice_id = _pick_catalog_voice(api_key, prompts["gender"], desk)
                db.session.commit()
                _log("heygen_create", resource="voice", desk=desk, voice_id=row.voice_id)
            else:
                _log(
                    "heygen_roster",
                    resource="voice",
                    desk=desk,
                    status="reuse",
                    voice_id=row.voice_id,
                )

            reused = _reuse_if_complete()
            if reused:
                return reused
            raise RuntimeError("Reporter roster missing avatar_id or voice_id after ensure")
        except Exception as exc:
            # Keep any IDs we already paid for so the next bulletin can reuse them.
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
            "background": {"type": "color", "value": "#060807"},
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


def _clip_key(clip: dict) -> tuple:
    role = clip.get("role")
    if role == "reporter":
        return (role, clip.get("desk"), clip.get("topic"))
    if role == "anchor_handoff":
        return (role, clip.get("topic"), clip.get("name"))
    return (role,)


def _fill_handoff_scripts(scripts: dict) -> dict:
    """Ensure each reporter has an anchor handoff line, even on older broadcasts."""
    from glconnect.news_agent import _anchor_handoff_text

    filled = dict(scripts or {})
    reporters = [dict(row) for row in (filled.get("reporters") or [])]
    previous = None
    for row in reporters:
        if not (row.get("handoff") or "").strip():
            row["handoff"] = _anchor_handoff_text(row, previous)
        previous = row
    filled["reporters"] = reporters
    return filled


def heygen_clips_missing_handoffs(scripts: dict, clips) -> bool:
    reporters = (scripts or {}).get("reporters") or []
    if not reporters:
        return False
    have = {
        clip.get("topic")
        for clip in (clips or [])
        if isinstance(clip, dict) and clip.get("role") == "anchor_handoff" and clip.get("url")
    }
    return any(row.get("topic") not in have for row in reporters)


def _reusable_clip_index(existing_clips) -> dict:
    index = {}
    for clip in existing_clips or []:
        if not isinstance(clip, dict):
            continue
        if clip.get("status") == "completed" and clip.get("url"):
            index[_clip_key(clip)] = clip
    return index


def _safe_task_id(task_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", task_id or "")
    if not cleaned:
        raise ValueError("invalid task id")
    return cleaned


def news_video_dir() -> str:
    path = os.path.abspath(os.path.join("glconnect", "static", "news_video"))
    os.makedirs(path, exist_ok=True)
    return path


def bulletin_mp4_path(task_id: str) -> str:
    return os.path.join(news_video_dir(), f"bulletin_{_safe_task_id(task_id)}.mp4")


def bulletin_file_url(task_id: str) -> str:
    return f"/routes2/news/bulletin/{_safe_task_id(task_id)}.mp4"


def bulletin_file_ready(task_id: str) -> bool:
    try:
        path = bulletin_mp4_path(task_id)
    except ValueError:
        return False
    return os.path.isfile(path) and os.path.getsize(path) > 0


def _grojingle_path() -> str | None:
    filename = "grojingle.mp4"
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video", filename),
        os.path.join(os.getcwd(), "video", filename),
        f"/usr/src/appdir/video/{filename}",
        os.path.abspath(os.path.join("video", filename)),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _probe_duration(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        return max(float((result.stdout or "").strip() or "0"), 0.1)
    except ValueError:
        return 1.0


def _has_audio_stream(path: str) -> bool:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return bool((result.stdout or "").strip())


def _materialize_video(source: str, dest: str) -> None:
    if os.path.isfile(source):
        shutil.copyfile(source, dest)
        return
    with requests.get(source, stream=True, timeout=(15, 180)) as response:
        response.raise_for_status()
        with open(dest, "wb") as handle:
            for chunk in response.iter_content(256 * 1024):
                if chunk:
                    handle.write(chunk)
    if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
        raise RuntimeError("Downloaded an empty video clip")


def assemble_bulletin_mp4(task_id: str, clips: list) -> str:
    """Stitch bumper + clips + bumper into one 1280x720 MP4. Returns the file path."""
    ready = [
        clip.get("url")
        for clip in (clips or [])
        if isinstance(clip, dict) and clip.get("status") == "completed" and clip.get("url")
    ]
    if not ready:
        raise RuntimeError("No completed clips to combine")

    bumper = _grojingle_path()
    sources = ([bumper] if bumper else []) + ready + ([bumper] if bumper else [])
    output_path = bulletin_mp4_path(task_id)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="news_bulletin_") as tmpdir:
        local_paths = []
        for index, source in enumerate(sources):
            dest = os.path.join(tmpdir, f"part_{index:02d}.mp4")
            _materialize_video(source, dest)
            local_paths.append(dest)

        filters = []
        concat_labels = []
        for index, path in enumerate(local_paths):
            filters.append(
                f"[{index}:v]scale=1280:720:force_original_aspect_ratio=decrease:flags=bicubic,"
                f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x060807,setsar=1,fps=30,format=yuv420p[v{index}]"
            )
            if _has_audio_stream(path):
                filters.append(
                    f"[{index}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                    f"aresample=async=1:first_pts=0[a{index}]"
                )
            else:
                duration = _probe_duration(path)
                filters.append(
                    f"anullsrc=r=44100:cl=stereo:d={duration:.3f},aformat=sample_fmts=fltp:"
                    f"sample_rates=44100:channel_layouts=stereo[a{index}]"
                )
            concat_labels.append(f"[v{index}][a{index}]")

        filter_complex = ";".join(filters) + (
            f";{''.join(concat_labels)}concat=n={len(local_paths)}:v=1:a=1[v][a]"
        )
        cmd = ["ffmpeg", "-y"]
        for path in local_paths:
            cmd.extend(["-i", path])
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ])
        _log("heygen_assemble", status="start", parts=len(local_paths), bumper=bool(bumper))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0 or not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            err = (result.stderr or result.stdout or "ffmpeg failed")[-400:]
            raise RuntimeError(err)

    return output_path


def generate_video_bulletin(task_id: str, scripts: dict, merge_result, existing_clips=None) -> dict:
    """Create HeyGen clips from saved scripts. Reuse completed clips, avatars, and voices."""
    warnings = []
    clips = []
    reusable = _reusable_clip_index(existing_clips)
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
    scripts = _fill_handoff_scripts(scripts)
    merge_result({"scripts": scripts})
    reporters = scripts.get("reporters") or []
    _log(
        "heygen_scripts",
        intro_chars=len(intro),
        outro_chars=len(outro),
        reporters=len(reporters),
    )

    state = {"status": "processing", "clips": clips, "warnings": warnings, "final_url": None}

    def persist():
        merge_result({
            "heygen": {
                "status": state["status"],
                "clips": [_public_clip(item) for item in clips],
                "warnings": warnings,
                "final_url": state.get("final_url"),
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
                "anchor_handoff",
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
        previous = reusable.get(_clip_key(clip))
        if previous:
            clip["status"] = "completed"
            clip["url"] = previous.get("url")
            clip["video_id"] = previous.get("video_id")
            clip["error"] = None
            clips.append(clip)
            _log(
                "heygen_skip",
                reason="clip_reuse",
                role=clip.get("role"),
                desk=clip.get("desk"),
                topic=clip.get("topic"),
            )
            persist()
            return clip
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
        handoff = (reporter.get("handoff") or "").strip()
        queue_and_render(
            _clip_record(
                role="anchor_handoff",
                name=ANCHOR_NAME,
                topic=topic,
                status="queued",
            )
            | {
                "avatar_id": ANCHOR_AVATAR_ID,
                "voice_id": ANCHOR_VOICE_ID,
                "script": handoff,
                "title": f"GRO News handoff {name} {task_id[:8]}",
            }
        )
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
    if completed:
        persist()
        try:
            assemble_bulletin_mp4(task_id, clips)
            state["final_url"] = bulletin_file_url(task_id)
            _log("heygen_assemble", status="ok", url=state["final_url"])
        except Exception as exc:
            _log("heygen_assemble", status="failed", error=str(exc)[:240])
    state["status"] = status
    _log(
        "heygen_summary",
        status=status,
        completed=len(completed),
        failed=len(failed),
        reused=len(reusable),
        desks=seen_desks,
        final=bool(state.get("final_url")),
    )
    persist()
    return {
        "status": status,
        "clips": [_public_clip(item) for item in clips],
        "warnings": warnings,
        "final_url": state.get("final_url"),
    }
