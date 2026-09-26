"""
Music Live Agent - ADK agent for Gemini Live API (bidi-demo architecture).
Uses native audio model for natural voice responses.
"""

import contextvars
import json
import os
from typing import Optional

# Context for current WebSocket session (user_id, base_url)
_music_live_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "music_live_ctx", default={"user_id": None, "base_url": ""}
)


def _ctx():
    return _music_live_ctx.get()


def set_music_live_context(user_id: Optional[int], base_url: str):
    _music_live_ctx.set({"user_id": user_id, "base_url": base_url or ""})


def _url_song(song_id: int) -> str:
    """Match playlist2 route: /playlist2/song/<song_id>/file"""
    base = _ctx().get("base_url", "").rstrip("/")
    path = f"/playlist2/song/{song_id}/file"
    return f"{base}{path}" if base else path


def _url_download(download_id: int) -> str:
    """Match playlist2 route: /playlist2/download/<download_id>/file"""
    base = _ctx().get("base_url", "").rstrip("/")
    path = f"/playlist2/download/{download_id}/file"
    return f"{base}{path}" if base else path


def _approved_filter():
    from glconnect.models import db, Song
    return db.or_(Song.approval_status.is_(None), Song.approval_status == "approved")


def search_songs(query: str) -> str:
    """
    Search GLC Radio / ElevenLabs originals only.
    Invocation: ONLY when the user explicitly asks to search, find, or play a specific song/artist (e.g. 'find X', 'play Y', 'search for Z').
    Do NOT call for greetings ('hi', 'hello', 'can you hear me') or small talk.
    Returns matching songs with song_id, name, artist, play_url, and cover_image.
    """
    from glconnect.eleven_catalog import search_eleven_catalog

    query = (query or "").strip()
    if not query:
        return json.dumps({"found": 0, "songs": [], "success": False})

    base = _ctx().get("base_url", "").rstrip("/")
    out = []
    for song in search_eleven_catalog(query)[:10]:
        path = song.get("path") or ""
        play_url = f"{base}{path}" if base and path.startswith("/") else path
        out.append({
            "id": song.get("id"),
            "song_id": song.get("song_id"),
            "download_id": None,
            "name": song.get("name"),
            "artist": song.get("artist"),
            "play_url": play_url,
            "cover_image": song.get("cover_image") or "/static/uploads/default_cover.jpg",
        })
    return json.dumps({
        "success": True,
        "message": f"Found {len(out)} matching GLC Radio originals.",
        "action": {"type": "search_results", "songs": out},
    })


def play_song(song_id: Optional[int] = None, download_id: Optional[int] = None) -> str:
    """
    Play a specific song. Use after search_songs when the user wants to listen.
    Requires song_id (artist uploads) or download_id (YouTube downloads).
    Returns a JSON with success, message, and action for the client to play the audio.
    """
    from glconnect.voc import SessionLocal
    from glconnect.models import Song
    from glconnect.eleven_catalog import is_eleven_song

    if song_id:
        session = SessionLocal()
        try:
            song = session.query(Song).get(song_id)
            if song and is_eleven_song(song):
                url = _url_song(song_id)
                return json.dumps({
                    "success": True,
                    "message": f"Playing {song.name or 'track'} by {song.artist or 'GLC Radio'}",
                    "action": {"type": "play", "url": url, "name": song.name or "Track", "artist": song.artist or "GLC Radio", "song_id": song_id, "download_id": None},
                })
        finally:
            session.close()
    return json.dumps({"success": False, "message": "Song not found in the GLC Radio catalog"})


def add_song_to_playlist(song_id: Optional[int] = None, download_id: Optional[int] = None) -> str:
    """
    Add a song to the user's playlist. Same logic as manual add. Use song_id for artist uploads, download_id for YouTube downloads.
    Requires the user to be logged in.
    """
    ctx = _ctx()
    user_id = ctx.get("user_id")
    if not user_id:
        return json.dumps({"success": False, "message": "Please log in to add songs to your playlist."})

    from glconnect.voc import SessionLocal
    from glconnect.playlist_logic import add_to_playlist_impl

    session = SessionLocal()
    try:
        success, message, err_code = add_to_playlist_impl(session, user_id, song_id, download_id)
        if success:
            return json.dumps({"success": True, "message": message, "action": {"type": "add_to_playlist"}})
        return json.dumps({"success": False, "message": message})
    finally:
        session.close()


def download_song(song_id: Optional[int] = None, download_id: Optional[int] = None) -> str:
    """
    Get the download URL for a song so the user can save it. Use song_id or download_id.
    Returns a JSON with success, message, and action for the client to trigger download.
    """
    from glconnect.voc import SessionLocal
    from glconnect.models import Song
    from glconnect.eleven_catalog import is_eleven_song

    if song_id:
        session = SessionLocal()
        try:
            song = session.query(Song).get(song_id)
            if song and is_eleven_song(song):
                url = _url_song(song_id)
                fname = f"{song.artist or 'GLC Radio'} - {song.name or 'track'}.mp3".replace("/", "-")
                return json.dumps({
                    "success": True,
                    "message": f"Download ready: {song.name or 'track'}",
                    "action": {"type": "download", "url": url, "filename": fname},
                })
        finally:
            session.close()
    return json.dumps({"success": False, "message": "Song not found in the GLC Radio catalog"})


def remove_song_from_playlist(song_id: Optional[int] = None, download_id: Optional[int] = None) -> str:
    """
    Remove a song from the user's playlist. Same logic as manual remove. Use list_my_playlist first to get song_id or download_id.
    Requires the user to be logged in.
    """
    ctx = _ctx()
    user_id = ctx.get("user_id")
    if not user_id:
        return json.dumps({"success": False, "message": "Please log in to remove songs from your playlist."})

    from glconnect.voc import SessionLocal
    from glconnect.playlist_logic import remove_from_playlist_impl

    session = SessionLocal()
    try:
        success, message, err_code = remove_from_playlist_impl(session, user_id, song_id, download_id)
        if success:
            return json.dumps({"success": True, "message": message, "action": {"type": "remove_from_playlist"}})
        return json.dumps({"success": False, "message": message})
    finally:
        session.close()


def list_my_playlist() -> str:
    """
    List all songs in the user's playlist. Returns songs with song_id (artist uploads) or download_id (YouTube).
    Use when the user asks 'what's in my playlist' or when they want to play a song from the playlist.
    To play a song from this list, call play_song(song_id=X) or play_song(download_id=Y) with the ID from the result.
    Requires the user to be logged in.
    """
    ctx = _ctx()
    user_id = ctx.get("user_id")
    if not user_id:
        return json.dumps({"success": False, "message": "Please log in to view your playlist."})

    from glconnect.voc import SessionLocal
    from glconnect.models import Playlist, Song
    from glconnect.eleven_catalog import is_eleven_song

    session = SessionLocal()
    try:
        playlist = session.query(Playlist).filter_by(user_id=user_id).all()
        if not playlist:
            return json.dumps({"success": True, "count": 0, "songs": [], "message": "Your playlist is empty."})
        out = []
        for entry in playlist:
            if not entry.song_id:
                continue
            song = session.query(Song).get(entry.song_id)
            if not song or not is_eleven_song(song):
                continue
            out.append({
                "name": (song.name or "").strip() or "Untitled",
                "artist": song.artist or "GLC Radio",
                "song_id": song.id,
                "download_id": None,
            })
        return json.dumps({"success": True, "count": len(out), "songs": out})
    finally:
        session.close()


def request_transcript() -> str:
    """
    Call this when the user asks for a transcript of the conversation, e.g. 'give me the transcript',
    'show our conversation', 'what did we say', 'transcript please'. Triggers the client to display it.
    """
    return json.dumps({
        "success": True,
        "message": "Here's the transcript.",
        "action": {"type": "show_transcript"},
    })


def get_catalog_suggestions() -> str:
    """
    Get a list of available artists and popular songs from the catalog.
    Invocation: ONLY when search_songs returned no results, OR when the user explicitly asks 'what do you have?', 'what can I listen to?', 'show me options'.
    Do NOT call for greetings ('hi', 'hello', 'can you hear me') or small talk.
    Returns a JSON with a list of artists and songs to suggest to the user.
    """
    from glconnect.eleven_catalog import list_eleven_catalog
    import random

    catalog = list_eleven_catalog()
    suggested_artists = list({track.get("artist") for track in catalog if track.get("artist")})
    random.shuffle(suggested_artists)
    suggested_songs = [{"name": track.get("name"), "artist": track.get("artist") or "GLC Radio"} for track in catalog]
    random.shuffle(suggested_songs)

    return json.dumps({
        "success": True,
        "message": "Here are some GLC Radio originals you can ask for.",
        "artists": suggested_artists[:5],
        "songs": suggested_songs[:5]
    })


MUSIC_INSTRUCTION = """Music assistant for Ink Studio. Scope: search, play, playlist, download only.

Rules:
- Be brief. Greetings ('hi','hello','can you hear me')→short verbal reply only, NO tools.
- Tools only when user explicitly asks for music. Play→use IDs from last search/playlist result; MUST call play_song().
- search_songs empty→call get_catalog_suggestions()."""


# Create agent - must be done after tools are defined
from google.adk.agents import Agent

music_agent = Agent(
    name="music_agent",
    model=os.getenv("MUSIC_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025"),
    tools=[search_songs, play_song, add_song_to_playlist, remove_song_from_playlist, download_song, list_my_playlist, request_transcript, get_catalog_suggestions],
    instruction=MUSIC_INSTRUCTION,
)
