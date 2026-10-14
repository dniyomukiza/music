"""Grok Imagine video bulletins for GLC TV news.

Started only from the admin button or POST /routes2/news/video/<task_id>,
after the radio bulletin has finished. Each presenter is a still in
glconnect/static/news_faces plus that person's Grok voice. Clips are at most
15 seconds. The finished MP4 replaces the file TV already plays.
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
import tempfile
import time

import requests

XAI_BASE = "https://api.x.ai/v1"
VIDEO_MODEL = os.getenv("GROK_VIDEO_MODEL", "grok-imagine-video-1.5")
MAX_SECONDS = 15
WORDS_PER_SECOND = 2.4

FACE_BY_NAME = {
    "anchor": "anchor.png",
    "ernest": "ernest.png",
    "isabella": "isabella.png",
    "mark": "mark.png",
    "edith": "edith.png",
    "clara": "clara.png",
    "james": "james.png",
}
FACE_BY_DESK = {
    "sports": "ernest",
    "finance": "isabella",
    "tech": "mark",
    "politics": "edith",
    "health": "clara",
    "news": "james",
    "other": "james",
}


def _log(event: str, **fields) -> None:
    extras = " ".join(f"{key}={value!r}" for key, value in fields.items())
    print(f"{event} {extras}".strip())


def _log_model_error(issue: str) -> None:
    text = str(issue or "unknown").replace("\n", " ").strip()
    if len(text) > 400:
        text = text[:400] + "..."
    print(f"ERROR: model provider=xai model={VIDEO_MODEL} issue={text}")


def _xai_key() -> str:
    return (os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY") or os.getenv("GROK_API") or "").strip()


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


def _video_asset(filename: str) -> str | None:
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video", filename),
        os.path.join(os.getcwd(), "video", filename),
        f"/usr/src/appdir/video/{filename}",
        f"/liqfolder/video/{filename}",
        os.path.abspath(os.path.join("video", filename)),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _face_path(person: str) -> str:
    filename = FACE_BY_NAME.get((person or "").strip().lower())
    if not filename:
        raise RuntimeError(f"No face is assigned for {person}")
    candidates = [
        os.path.join("glconnect", "static", "news_faces", filename),
        os.path.join("/usr/src/appdir", "glconnect", "static", "news_faces", filename),
        os.path.abspath(os.path.join("glconnect", "static", "news_faces", filename)),
    ]
    for path in candidates:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return path
    raise RuntimeError(f"Missing presenter still glconnect/static/news_faces/{filename}")


def _face_data_uri(person: str) -> str:
    path = _face_path(person)
    encoded = base64.b64encode(open(path, "rb").read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _voice_for(person: str) -> str:
    from glconnect.news_agent import ANCHOR_VOICE, _reporter_for_name

    key = (person or "").strip().lower()
    if key == "anchor":
        return ANCHOR_VOICE
    row = _reporter_for_name(key)
    if row and row.get("voice"):
        return row["voice"]
    raise RuntimeError(f"No Grok voice is assigned for {person}")


def _person_for_reporter(row: dict) -> str:
    name = (row.get("name") or "").strip().lower()
    if name in FACE_BY_NAME and name != "anchor":
        return name
    desk = (row.get("desk") or row.get("category") or "news").strip().lower()
    return FACE_BY_DESK.get(desk, "james")


def _chunks(text: str) -> list[str]:
    spoken = " ".join((text or "").split())
    if not spoken:
        return []
    max_words = max(8, int(MAX_SECONDS * WORDS_PER_SECOND) - 4)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", spoken) if part.strip()]
    if not sentences:
        sentences = [spoken]
    chunks = []
    current = []
    words = 0
    for sentence in sentences:
        count = len(sentence.split())
        if current and words + count > max_words:
            chunks.append(" ".join(current))
            current = [sentence]
            words = count
        else:
            current.append(sentence)
            words += count
    if current:
        chunks.append(" ".join(current))
    return chunks


def _duration_for(text: str) -> int:
    seconds = max(6, min(MAX_SECONDS, round(max(1, len(text.split())) / WORDS_PER_SECOND)))
    return min((6, 10, 15), key=lambda allowed: abs(allowed - seconds))


def _scene_prompt(person: str, script: str) -> str:
    return (
        f"The person in the reference image is the GLC Media presenter {person}. "
        "Keep that same face. Waist-up, standing in the GLC studio, looking into the camera. "
        "They speak the lines below in a natural news voice, with lip movement matched to the speech. "
        "No captions, no other logos, no second person. "
        f"Spoken lines: {script}"
    )


def _start_clip(api_key: str, person: str, script: str) -> str:
    body = {
        "model": VIDEO_MODEL,
        "prompt": _scene_prompt(person, script),
        "duration": _duration_for(script),
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "reference_images": [{"url": _face_data_uri(person)}],
        "reference_audios": [{"voice_id": _voice_for(person)}],
    }
    response = requests.post(
        f"{XAI_BASE}/videos/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if not response.ok:
        detail = (response.text or "").strip()[:240]
        raise RuntimeError(f"Grok video failed ({response.status_code}): {detail}")
    request_id = str((response.json() or {}).get("request_id") or "").strip()
    if not request_id:
        raise RuntimeError("Grok video returned no request_id")
    return request_id


def _poll_clip(api_key: str, request_id: str) -> str:
    deadline = time.time() + 720
    while time.time() < deadline:
        response = requests.get(
            f"{XAI_BASE}/videos/{request_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if not response.ok:
            raise RuntimeError(f"Grok video poll failed ({response.status_code}): {(response.text or '')[:240]}")
        data = response.json() or {}
        status = str(data.get("status") or "").lower()
        if status == "done":
            url = str((data.get("video") or {}).get("url") or "").strip()
            if not url:
                raise RuntimeError("Grok video finished without a URL")
            return url
        if status in {"failed", "expired"}:
            error = data.get("error") or {}
            message = error.get("message") if isinstance(error, dict) else status
            raise RuntimeError(f"Grok video {status}: {message}")
        time.sleep(5)
    raise RuntimeError(f"Grok video {request_id} timed out")


def _download(url: str, dest: str) -> None:
    response = requests.get(url, timeout=180)
    if not response.ok or len(response.content) < 64:
        raise RuntimeError(f"Grok video download failed ({response.status_code})")
    with open(dest, "wb") as handle:
        handle.write(response.content)


def _has_audio(path: str) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=30,
    )
    return bool((result.stdout or "").strip())


def _probe_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=30,
    )
    try:
        return max(float((result.stdout or "").strip() or "0"), 0.1)
    except ValueError:
        return 1.0


def _tv_file_ready(path: str) -> bool:
    if not os.path.isfile(path) or os.path.getsize(path) < 1024:
        return False
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", path],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0 and (result.stdout or "").strip().lower().startswith("h264")


def _stitch(paths: list[str], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    filters = []
    labels = []
    for index, path in enumerate(paths):
        filters.append(
            f"[{index}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x060807,setsar=1,fps=30,format=yuv420p[v{index}]"
        )
        if _has_audio(path):
            filters.append(
                f"[{index}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                f"aresample=async=1:first_pts=0[a{index}]"
            )
        else:
            filters.append(
                f"anullsrc=r=44100:cl=stereo:d={_probe_duration(path):.3f}[a{index}]"
            )
        labels.append(f"[v{index}][a{index}]")
    filter_complex = ";".join(filters) + f";{''.join(labels)}concat=n={len(paths)}:v=1:a=1[v][a]"
    cmd = ["ffmpeg", "-y"]
    for path in paths:
        cmd.extend(["-i", path])
    cmd.extend([
        "-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", output_path,
    ])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0 or not _tv_file_ready(output_path):
        err = (result.stderr or result.stdout or "ffmpeg failed")[-400:]
        raise RuntimeError(err)


def _tv_destinations() -> list[str]:
    name = "The Weeknd - final_news_broadcast.mp4"
    paths = []
    seen = set()
    for base in ("", "/usr/src/appdir", "/liqfolder"):
        prefix = f"{base}/" if base else ""
        path = f"{prefix}glconnect/static/ytautovid/{name}"
        key = os.path.abspath(path)
        if key not in seen:
            seen.add(key)
            paths.append(path)
    return paths


def publish_tv_news(source_path: str) -> str:
    if not _tv_file_ready(source_path):
        issue = f"Refusing to replace the TV file. News video has no H.264 picture: {source_path}"
        _log_model_error(issue)
        raise RuntimeError(issue)
    targets = [dest for dest in _tv_destinations() if os.path.isdir(os.path.dirname(dest))]
    if not targets:
        dest = _tv_destinations()[0]
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        targets = [dest]
    published = ""
    for dest in targets:
        staging = os.path.join(os.path.dirname(dest), ".final_news_broadcast.writing.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", source_path, "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "main", "-level", "4.0",
            "-g", "60", "-keyint_min", "60", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
            "-movflags", "+faststart", staging,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0 or not _tv_file_ready(staging):
            if os.path.isfile(staging):
                os.remove(staging)
            err = (result.stderr or result.stdout or "TV normalize failed")[-400:]
            _log_model_error(err)
            raise RuntimeError(err)
        os.replace(staging, dest)
        published = dest
        _log("grok_tv", status="replaced", path=dest, bytes=os.path.getsize(dest))
    return published


def _scenes(scripts: dict) -> list[dict]:
    scenes = []
    intro = (scripts.get("intro") or "").strip()
    if intro:
        scenes.append({"role": "anchor_intro", "person": "anchor", "name": "Anchor", "text": intro})
    for row in scripts.get("reporters") or []:
        if not isinstance(row, dict):
            continue
        person = _person_for_reporter(row)
        name = row.get("name") or person
        handoff = (row.get("handoff") or "").strip()
        script = (row.get("script") or "").strip()
        if handoff:
            scenes.append({"role": "anchor_handoff", "person": "anchor", "name": "Anchor", "topic": row.get("topic"), "text": handoff})
        if script:
            scenes.append({"role": "reporter", "person": person, "name": name, "topic": row.get("topic"), "text": script})
    outro = (scripts.get("outro") or "").strip()
    if outro:
        scenes.append({"role": "anchor_outro", "person": "anchor", "name": "Anchor", "text": outro})
    return scenes


def generate_video_bulletin(task_id: str, scripts: dict, merge_result, existing_clips=None) -> dict:
    """Create a Grok TV bulletin from the saved radio scripts."""
    del existing_clips
    warnings = []
    clips = []
    api_key = _xai_key()
    if not api_key:
        state = {
            "provider": "grok",
            "status": "failed",
            "clips": [],
            "warnings": ["XAI_API_KEY is not set. Video bulletin was not generated."],
            "final_url": None,
        }
        _log_model_error(state["warnings"][0])
        merge_result({"video": state})
        return state

    scenes = _scenes(scripts or {})
    if not scenes:
        state = {
            "provider": "grok",
            "status": "failed",
            "clips": [],
            "warnings": ["No scripts were available for the video bulletin."],
            "final_url": None,
        }
        merge_result({"video": state})
        return state

    state = {"provider": "grok", "status": "processing", "clips": clips, "warnings": warnings, "final_url": None}

    def persist():
        merge_result({"video": dict(state, clips=list(clips), warnings=list(warnings))})

    persist()
    spoken_paths = []
    with tempfile.TemporaryDirectory(prefix="grok_news_") as tmpdir:
        for index, scene in enumerate(scenes):
            for part_index, chunk in enumerate(_chunks(scene["text"])):
                label = f"{scene['role']} {scene['name']}"
                try:
                    _log("grok_clip", person=scene["person"], role=scene["role"], part=part_index)
                    request_id = _start_clip(api_key, scene["person"], chunk)
                    url = _poll_clip(api_key, request_id)
                    dest = os.path.join(tmpdir, f"part_{index:02d}_{part_index:02d}.mp4")
                    _download(url, dest)
                    spoken_paths.append(dest)
                    clips.append({
                        "role": scene["role"],
                        "name": scene["name"],
                        "topic": scene.get("topic"),
                        "status": "completed",
                    })
                except Exception as exc:
                    message = str(exc)[:400]
                    _log_model_error(f"{label}: {message}")
                    warnings.append(f"{label}: {message}")
                    clips.append({
                        "role": scene["role"],
                        "name": scene["name"],
                        "topic": scene.get("topic"),
                        "status": "failed",
                        "error": message,
                    })
                persist()

        completed = [clip for clip in clips if clip.get("status") == "completed"]
        failed = [clip for clip in clips if clip.get("status") == "failed"]
        if not spoken_paths:
            state["status"] = "failed"
            persist()
            return state

        pieces = []
        opener = _video_asset("tvsweeper.mp4")
        closer = _video_asset("grojingle.mp4")
        if opener:
            pieces.append(opener)
        else:
            _log_model_error("video/tvsweeper.mp4 is missing; bulletin will not open with the sweeper")
        pieces.extend(spoken_paths)
        if closer:
            pieces.append(closer)
        output_path = bulletin_mp4_path(task_id)
        try:
            _stitch(pieces, output_path)
            publish_tv_news(output_path)
            state["final_url"] = bulletin_file_url(task_id)
            state["status"] = "completed" if not failed else "partial"
        except Exception as exc:
            message = str(exc)[:400]
            _log_model_error(f"bulletin assemble failed: {message}")
            warnings.append(message)
            state["status"] = "partial" if completed else "failed"
        persist()
        return state
