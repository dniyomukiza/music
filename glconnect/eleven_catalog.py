"""Public music search is limited to ElevenLabs / GLC Radio originals.

Artist uploads (static/afro) and YouTube rips (static/ytauto) stay off the
/mybook/music catalog so the player does not surface third-party recordings.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

ELEVEN_FOLDER = "eleven"
ELEVEN_AUDIO_EXTS = {".mp3", ".ogg", ".m4a", ".wav"}
ELEVEN_PATH_MARKERS = ("/static/eleven/", "static/eleven/", "/eleven/")


def _eleven_search_dirs() -> list[str]:
    dirs: list[str] = []
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            dirs.append(os.path.join(current_app.root_path, "static", ELEVEN_FOLDER))
    except Exception:
        pass
    dirs.extend(
        [
            os.path.join(os.getcwd(), "glconnect", "static", ELEVEN_FOLDER),
            os.path.join(os.getcwd(), "static", ELEVEN_FOLDER),
            "/usr/src/appdir/glconnect/static/eleven",
        ]
    )
    out: list[str] = []
    seen: set[str] = set()
    for directory in dirs:
        try:
            real = os.path.realpath(directory)
        except OSError:
            continue
        if real in seen or not os.path.isdir(real):
            continue
        seen.add(real)
        out.append(real)
    return out


def is_eleven_path(path: Optional[str]) -> bool:
    if not path:
        return False
    norm = path.replace("\\", "/").lower()
    return any(marker in norm for marker in ELEVEN_PATH_MARKERS)


def is_eleven_song(song: Any) -> bool:
    return is_eleven_path(getattr(song, "local_path", None))


def parse_eleven_title(filename: str) -> tuple[str, str]:
    stem = os.path.splitext(os.path.basename(filename))[0].strip()
    if " - " in stem:
        artist, name = stem.split(" - ", 1)
        return (artist.strip() or "GLC Radio"), (name.strip() or stem)
    return "GLC Radio", stem or "Untitled Track"


def scan_eleven_files() -> list[dict[str, str]]:
    seen: set[str] = set()
    files: list[dict[str, str]] = []
    for directory in _eleven_search_dirs():
        try:
            names = os.listdir(directory)
        except OSError:
            continue
        for filename in names:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ELEVEN_AUDIO_EXTS:
                continue
            key = filename.lower()
            if key in seen:
                continue
            abs_path = os.path.join(directory, filename)
            if not os.path.isfile(abs_path):
                continue
            seen.add(key)
            artist, name = parse_eleven_title(filename)
            files.append(
                {
                    "filename": filename,
                    "directory": directory,
                    "artist": artist,
                    "name": name,
                    "abs_path": abs_path,
                }
            )
    files.sort(key=lambda track: (track["artist"].lower(), track["name"].lower()))
    return files


def resolve_eleven_file(filename: str) -> Optional[str]:
    safe = os.path.basename((filename or "").replace("\\", "/"))
    if not safe or safe in (".", "..") or "/" in safe:
        return None
    if os.path.splitext(safe)[1].lower() not in ELEVEN_AUDIO_EXTS:
        return None
    for directory in _eleven_search_dirs():
        candidate = os.path.realpath(os.path.join(directory, safe))
        root = os.path.realpath(directory)
        try:
            if os.path.commonpath([root, candidate]) != root:
                continue
        except ValueError:
            continue
        if os.path.isfile(candidate):
            return candidate
    return None


def eleven_play_path(filename: str) -> str:
    encoded = quote(os.path.basename(filename), safe="")
    try:
        from flask import url_for, has_app_context

        if has_app_context():
            return url_for("playlist2.serve_eleven_file", filename=os.path.basename(filename))
    except Exception:
        pass
    return f"/playlist2/eleven/{encoded}"


def _clip(value: str, limit: int = 100) -> str:
    return (value or "").strip()[:limit]


def _index_eleven_songs_by_filename() -> dict[str, Any]:
    from glconnect.models import Song

    indexed: dict[str, Any] = {}
    try:
        songs = Song.query.filter(Song.local_path.isnot(None)).all()
    except Exception:
        logger.exception("Could not load songs while indexing ElevenLabs catalog")
        return indexed
    for song in songs:
        if not is_eleven_song(song):
            continue
        filename = os.path.basename(song.local_path.replace("\\", "/"))
        if filename:
            indexed[filename] = song
    return indexed


def _sync_eleven_songs(files: list[dict[str, str]]) -> dict[str, Any]:
    from glconnect.models import Song, db

    indexed = _index_eleven_songs_by_filename()
    created = False
    try:
        for track in files:
            if track["filename"] in indexed:
                continue
            song = Song(
                name=_clip(track["name"]),
                artist=_clip(track["artist"]),
                local_path=f"glconnect/static/eleven/{track['filename']}",
                approval_status="approved",
            )
            db.session.add(song)
            created = True
        if created:
            db.session.commit()
            indexed = _index_eleven_songs_by_filename()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.exception("Could not sync ElevenLabs files into the songs table")
    return indexed


def _payload(track: dict[str, str], song: Any = None) -> dict[str, Any]:
    song_id = getattr(song, "id", None)
    return {
        "id": song_id or track["filename"],
        "song_id": song_id,
        "download_id": None,
        "name": track["name"],
        "artist": track["artist"],
        "path": eleven_play_path(track["filename"]),
        "cover_image": None,
        "artist_profile_pic": None,
        "filename": track["filename"],
    }


def list_eleven_catalog(*, sync_db: bool = True) -> list[dict[str, Any]]:
    files = scan_eleven_files()
    indexed = _sync_eleven_songs(files) if sync_db else _index_eleven_songs_by_filename()
    return [_payload(track, indexed.get(track["filename"])) for track in files]


def _matches_query(track: dict[str, Any], query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return True
    blob = f"{track.get('artist', '')} {track.get('name', '')} {track.get('filename', '')}".lower()
    if q in blob:
        return True
    words = [word for word in q.split() if len(word) > 1]
    return bool(words) and all(word in blob for word in words)


def search_eleven_catalog(query: str) -> list[dict[str, Any]]:
    q = (query or "").strip()
    catalog = list_eleven_catalog()
    if not q:
        return catalog
    return [track for track in catalog if _matches_query(track, q)]


def suggest_eleven_catalog(query: str, *, limit: int = 5) -> dict[str, list[dict[str, Any]]]:
    matches = search_eleven_catalog(query)
    artists: list[dict[str, Any]] = []
    seen_artists: set[str] = set()
    songs: list[dict[str, Any]] = []
    for track in matches:
        artist = (track.get("artist") or "").strip()
        key = artist.lower()
        if artist and key not in seen_artists and len(artists) < limit:
            seen_artists.add(key)
            artists.append({"id": None, "name": artist, "type": "artist"})
        if len(songs) < limit:
            songs.append(
                {
                    "id": track.get("id"),
                    "song_id": track.get("song_id"),
                    "download_id": None,
                    "name": track.get("name"),
                    "artist": artist,
                    "type": "song",
                }
            )
    return {"artists": artists, "songs": songs}


def eleven_songs_for_artist(artist_name: str = "") -> list[dict[str, Any]]:
    name = (artist_name or "").strip().lower()
    catalog = list_eleven_catalog()
    if not name:
        return catalog
    return [
        track
        for track in catalog
        if name == (track.get("artist") or "").lower() or name in (track.get("artist") or "").lower()
    ]
