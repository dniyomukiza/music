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
    Search for songs or artists in the music catalog.
    Use when the user asks about a song, artist, or wants to find music.
    Returns matching songs with song_id, download_id, name, artist, and play_url.
    """
    from glconnect.voc import SessionLocal
    from glconnect.models import db, Song, Artist, DownloadedSong

    query = (query or "").strip().lower()
    if not query:
        return json.dumps({"found": 0, "songs": []})

    session = SessionLocal()
    try:
        all_songs_data = []
        seen_keys = set()
        approved = _approved_filter()

        def add_unique(sid, did, name, artist, url):
            key = f"{name.lower()}|{artist.lower()}"
            if key in seen_keys:
                return
            seen_keys.add(key)
            all_songs_data.append({
                "id": sid or (2000000 + did),
                "song_id": sid,
                "download_id": did,
                "name": name,
                "artist": artist,
                "play_url": url
            })

        # 1. Priority: Artist exact match
        artist = session.query(Artist).filter(db.func.lower(Artist.artist_name) == query).first()
        if artist:
            songs = session.query(Song).filter_by(artist_id=artist.artist_id).filter(approved).limit(10).all()
            for s in songs:
                add_unique(s.id, None, s.name or "Untitled", artist.artist_name, _url_song(s.id))

        # 2. Search Song table (name or artist partial)
        if len(all_songs_data) < 10:
            songs = session.query(Song).filter(
                approved,
                db.or_(
                    db.func.lower(Song.name).like(f"%{query}%"),
                    db.func.lower(Song.artist).like(f"%{query}%")
                )
            ).limit(15).all()
            for s in songs:
                s_artist = s.artist or "Unknown"
                if s.artist_id:
                    a = session.query(Artist).get(s.artist_id)
                    if a: s_artist = a.artist_name
                add_unique(s.id, None, s.name or "Untitled", s_artist, _url_song(s.id))

        # 3. Search DownloadedSong table
        if len(all_songs_data) < 10:
            downloads = session.query(DownloadedSong).filter(
                db.or_(
                    db.func.lower(DownloadedSong.name).like(f"%{query}%"),
                    db.func.lower(DownloadedSong.artist).like(f"%{query}%")
                )
            ).limit(10).all()
            for d in downloads:
                add_unique(None, d.id, d.name or "Untitled", d.artist or "Unknown", _url_download(d.id))

        out = all_songs_data[:10]
        return json.dumps({"found": len(out), "songs": out, "success": True})
    finally:
        session.close()


def play_song(song_id: Optional[int] = None, download_id: Optional[int] = None) -> str:
    """
    Play a specific song. Use after search_songs when the user wants to listen.
    Requires song_id (artist uploads) or download_id (YouTube downloads).
    Returns a JSON with success, message, and action for the client to play the audio.
    """
    from glconnect.voc import SessionLocal
    from glconnect.models import Song, DownloadedSong

    if song_id:
        session = SessionLocal()
        try:
            song = session.query(Song).get(song_id)
            if song:
                url = _url_song(song_id)
                return json.dumps({
                    "success": True,
                    "message": f"Playing {song.name or 'track'} by {song.artist or 'Unknown'}",
                    "action": {"type": "play", "url": url, "name": song.name or "Track", "artist": song.artist or "Unknown", "song_id": song_id, "download_id": None},
                })
        finally:
            session.close()
    if download_id:
        session = SessionLocal()
        try:
            d = session.query(DownloadedSong).get(download_id)
            if d:
                url = _url_download(download_id)
                return json.dumps({
                    "success": True,
                    "message": f"Playing {d.name or 'track'} by {d.artist or 'Unknown'}",
                    "action": {"type": "play", "url": url, "name": d.name or "Track", "artist": d.artist or "Unknown", "song_id": None, "download_id": download_id},
                })
        finally:
            session.close()
    return json.dumps({"success": False, "message": "Song not found"})


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
    from glconnect.models import Song, DownloadedSong

    if song_id:
        session = SessionLocal()
        try:
            song = session.query(Song).get(song_id)
            if song:
                url = _url_song(song_id)
                fname = f"{song.artist or 'Unknown'} - {song.name or 'track'}.mp3".replace("/", "-")
                return json.dumps({
                    "success": True,
                    "message": f"Download ready: {song.name or 'track'}",
                    "action": {"type": "download", "url": url, "filename": fname},
                })
        finally:
            session.close()
    if download_id:
        session = SessionLocal()
        try:
            d = session.query(DownloadedSong).get(download_id)
            if d:
                url = _url_download(download_id)
                fname = f"{d.artist or 'Unknown'} - {d.name or 'track'}.mp3".replace("/", "-")
                return json.dumps({
                    "success": True,
                    "message": f"Download ready: {d.name or 'track'}",
                    "action": {"type": "download", "url": url, "filename": fname},
                })
        finally:
            session.close()
    return json.dumps({"success": False, "message": "Song not found"})


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
    from glconnect.models import Playlist, Song, Artist, DownloadedSong

    session = SessionLocal()
    try:
        playlist = session.query(Playlist).filter_by(user_id=user_id).all()
        if not playlist:
            return json.dumps({"success": True, "count": 0, "songs": [], "message": "Your playlist is empty."})
        out = []
        for entry in playlist:
            if entry.song_id:
                song = session.query(Song).get(entry.song_id)
                if song:
                    artist_name = song.artist or "Unknown"
                    if song.artist_id:
                        a = session.query(Artist).get(song.artist_id)
                        if a:
                            artist_name = a.artist_name
                    out.append({"name": (song.name or "").strip() or "Untitled", "artist": artist_name, "song_id": song.id, "download_id": None})
            elif entry.download_id:
                d = session.query(DownloadedSong).get(entry.download_id)
                if d:
                    out.append({"name": (d.name or "").strip() or "Untitled", "artist": d.artist or "Unknown", "song_id": None, "download_id": d.id})
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


MUSIC_INSTRUCTION = """You are a voice-controlled music assistant for the Ink Studio music dashboard. You provide the same functionality as the manual UI via voice commands.

Tools:
1. search_songs(query): Search songs/artists. Use this first when a user mentions a song or artist.
2. play_song(song_id or download_id): Start playback. CRITICAL: Playback only happens when you call this tool. Use IDs from search or playlist.
3. add_song_to_playlist(song_id or download_id): Add to user's playlist (requires login).
4. remove_song_from_playlist(song_id or download_id): Remove from user's playlist (requires login).
5. download_song(song_id or download_id): Get download link.
6. list_my_playlist(): List user's playlist (requires login).
7. request_transcript(): Display conversation transcript when requested.

Rules:
- You MUST call play_song() to trigger playback. Confirming play without calling it does nothing.
- To play from the playlist, call list_my_playlist() first to get IDs.
- Be conversational, confirm actions clearly, and use tools proactively to fulfill requests."""


# Create agent - must be done after tools are defined
from google.adk.agents import Agent

music_agent = Agent(
    name="music_agent",
    model=os.getenv("MUSIC_LIVE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025"),
    tools=[search_songs, play_song, add_song_to_playlist, remove_song_from_playlist, download_song, list_my_playlist, request_transcript],
    instruction=MUSIC_INSTRUCTION,
)
