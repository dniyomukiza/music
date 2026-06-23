"""
Music Voice Agent - Gemini-powered voice assistant for the music dashboard.
Users can ask questions about songs/artists and perform actions: play, download, add to playlist.
Config: GOOGLE_API_KEY or GEMINI_API_KEY via os.getenv (same as news_agent, blog, routes2).
"""

import os
import json
from typing import List, Dict, Any, Optional

from glconnect.ai_config import AIConfig


SYSTEM_INSTRUCTION = """You are a voice-controlled music assistant for the Ink Studio music dashboard. You provide the same functionality as the UI buttons, but via voice commands.

You have full access to the music database:
- Artist-uploaded songs (Song table) and YouTube-downloaded songs (DownloadedSong table)
- User playlists (Playlist table) for logged in users

Your tools (use them to fulfill requests):
1. search_songs(query) - Find songs/artists in the catalog. Always use this first when the user mentions a song or artist.
2. play_song(song_id or download_id) - Start playback. Use song_id for artist uploads, download_id for YouTube downloads.
3. add_song_to_playlist(song_id or download_id) - Add to user's playlist. Requires login.
4. download_song(song_id or download_id) - Get download link for the user to save the file.
5. list_my_playlist() - List songs in the user's playlist (requires login).

Voice command examples you should understand:
- "Play Rockabye" / "Play Rockabye by Clean Bandit" → search_songs then play_song
- "Add X to my playlist" → search_songs then add_song_to_playlist
- "Download X" / "I want to download X" → search_songs then download_song
- "What's in my playlist?" / "List my playlist" → list_my_playlist
- "Find songs by [artist]" / "Search for [song]" → search_songs

When you find songs via search_songs, use the song_id or download_id from the results for play/add/download. Be conversational and confirm actions clearly."""


def get_tools_for_gemini():
    """Return tool definitions for Gemini function calling (genai.types format)."""
    from google.generativeai.types import content_types
    return [
        content_types.FunctionDeclaration(
            name="search_songs",
            description="Search for songs or artists in the music catalog. Use when the user asks about a song, artist, or wants to find music. Returns matching songs with id, name, artist, song_id, download_id, and play_url.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - song name, artist name, or both (e.g. 'Rockabye Clean Bandit')"
                    }
                },
                "required": ["query"]
            }
        ),
        content_types.FunctionDeclaration(
            name="play_song",
            description="Play a specific song. Use after search_songs when the user wants to listen. Requires song_id (artist uploads) or download_id (YouTube downloads).",
            parameters={
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer", "description": "Song ID from songs table"},
                    "download_id": {"type": "integer", "description": "Download ID from downloaded_songs table"}
                }
            }
        ),
        content_types.FunctionDeclaration(
            name="add_song_to_playlist",
            description="Add a song to the user's playlist. Use song_id for artist uploads, download_id for YouTube downloads.",
            parameters={
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer", "description": "Song ID (artist uploads)"},
                    "download_id": {"type": "integer", "description": "Download ID (YouTube downloads)"}
                }
            }
        ),
        content_types.FunctionDeclaration(
            name="download_song",
            description="Get the download URL for a song so the user can save it. Use song_id or download_id.",
            parameters={
                "type": "object",
                "properties": {
                    "song_id": {"type": "integer", "description": "Song ID (artist uploads)"},
                    "download_id": {"type": "integer", "description": "Download ID (YouTube downloads)"}
                }
            }
        ),
        content_types.FunctionDeclaration(
            name="list_my_playlist",
            description="List all songs in the user's playlist. Use when the user asks 'what's in my playlist', 'list my playlist', 'show my playlist', etc. Requires user to be logged in.",
            parameters={"type": "object", "properties": {}}
        ),
    ]


def search_songs_impl(query: str, base_url: str = "") -> List[Dict[str, Any]]:
    """
    Search songs using the same logic as playlist2. Returns list of song dicts.
    base_url: e.g. 'https://glc.cool' for building absolute URLs.
    """
    from glconnect.models import db, Song, Artist, DownloadedSong
    from glconnect.playlist2 import _approved_songs_filter, get_all_songs_by_artist, check_song_file_exists
    from flask import url_for

    query = (query or "").strip().lower()
    if not query:
        return []

    seen_song_ids = set()
    seen_song_keys = set()
    all_songs_data = []

    def add_if_unique(song_data):
        sid = song_data["id"]
        skey = f"{(song_data.get('name') or '').lower()}|{(song_data.get('artist') or '').lower()}"
        if sid in seen_song_ids or skey in seen_song_keys:
            return
        seen_song_ids.add(sid)
        seen_song_keys.add(skey)
        all_songs_data.append(song_data)

    # Downloaded songs
    downloads = DownloadedSong.query.filter(
        db.or_(
            db.func.lower(DownloadedSong.name).like(f"%{query}%"),
            db.func.lower(DownloadedSong.artist).like(f"%{query}%")
        )
    ).limit(20).all()
    for d in downloads:
        name = (d.name or "").strip() or "Untitled Track"
        artist = d.artist or "Unknown"
        path = url_for("playlist2.serve_downloaded_song_file", download_id=d.id, _external=True)
        add_if_unique({
            "id": 2000000 + d.id,
            "song_id": None,
            "download_id": d.id,
            "name": name,
            "artist": artist,
            "path": path,
            "play_url": path,
        })

    # Artist exact match
    artist = Artist.query.filter(db.func.lower(Artist.artist_name) == query).first()
    if artist:
        songs_data = get_all_songs_by_artist(artist_id=artist.artist_id, artist_name=artist.artist_name, include_collaborations=True)
        for s in songs_data:
            path = s.get("path") or url_for("playlist2.serve_song_file", song_id=s["id"], _external=True)
            add_if_unique({
                **s,
                "play_url": path,
            })
        if all_songs_data:
            return all_songs_data

    # Song name partial match
    songs = Song.query.filter(db.func.lower(Song.name).like(f"%{query}%")).filter(_approved_songs_filter()).limit(20).all()
    if songs:
        first = songs[0]
        artist_id, artist_name = first.artist_id, first.artist
        if artist_id:
            a = Artist.query.get(artist_id)
            if a:
                artist_name = a.artist_name
        if artist_id or artist_name:
            songs_data = get_all_songs_by_artist(artist_id=artist_id, artist_name=artist_name)
            for s in songs_data:
                path = s.get("path") or url_for("playlist2.serve_song_file", song_id=s["id"], _external=True)
                add_if_unique({**s, "play_url": path})
            if all_songs_data:
                return all_songs_data

    # Song.artist partial match
    songs_artist = Song.query.filter(db.func.lower(Song.artist).like(f"%{query}%")).filter(_approved_songs_filter()).all()
    for song in songs_artist:
        if not check_song_file_exists(song):
            continue
        artist_name = song.artist or "Unknown"
        if song.artist_id:
            a = Artist.query.get(song.artist_id)
            if a:
                artist_name = a.artist_name
        song_name = (song.name or "").strip() or "Untitled Track"
        path = url_for("playlist2.serve_song_file", song_id=song.id, _external=True)
        add_if_unique({
            "id": song.id,
            "song_id": song.id,
            "download_id": None,
            "name": song_name,
            "artist": artist_name,
            "path": path,
            "play_url": path,
        })

    return all_songs_data


def run_agent_turn(user_message: str, user_id: Optional[int], base_url: str = "") -> Dict[str, Any]:
    """
    Process one user message with Gemini and tools. Returns response text and any actions for the client.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "Google API key not configured. Set GOOGLE_API_KEY or GEMINI_API_KEY.",
            "text": "I'm sorry, the voice assistant is not configured. Please contact support.",
            "actions": []
        }

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "Failed to initialize the voice assistant.",
            "actions": []
        }

    from google.generativeai.types import content_types
    tools_list = [content_types.Tool(function_declarations=get_tools_for_gemini())]
    model = genai.GenerativeModel(
        model_name=AIConfig.GEMINI_MODEL,
        tools=tools_list,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    actions = []

    def execute_tool(name: str, args: dict) -> str:
        nonlocal actions
        if name == "search_songs":
            q = args.get("query", "")
            results = search_songs_impl(q, base_url)
            # Simplify for the model
            out = []
            for s in results[:10]:
                out.append({
                    "id": s["id"],
                    "song_id": s.get("song_id"),
                    "download_id": s.get("download_id"),
                    "name": s.get("name"),
                    "artist": s.get("artist"),
                    "play_url": s.get("play_url"),
                })
            return json.dumps({"found": len(results), "songs": out})

        if name == "play_song":
            song_id = args.get("song_id")
            download_id = args.get("download_id")
            if song_id:
                from glconnect.models import Song
                from flask import url_for
                song = Song.query.get(song_id)
                if song:
                    path = url_for("playlist2.serve_song_file", song_id=song_id, _external=True)
                    actions.append({"type": "play", "url": path, "name": song.name or "Track", "artist": song.artist or "Unknown"})
                    return json.dumps({"success": True, "message": f"Playing {song.name or 'track'} by {song.artist or 'Unknown'}"})
            if download_id:
                from glconnect.models import DownloadedSong
                from flask import url_for
                d = DownloadedSong.query.get(download_id)
                if d:
                    path = url_for("playlist2.serve_downloaded_song_file", download_id=download_id, _external=True)
                    actions.append({"type": "play", "url": path, "name": d.name or "Track", "artist": d.artist or "Unknown"})
                    return json.dumps({"success": True, "message": f"Playing {d.name or 'track'} by {d.artist or 'Unknown'}"})
            return json.dumps({"success": False, "message": "Song not found"})

        if name == "add_song_to_playlist":
            if not user_id:
                return json.dumps({"success": False, "message": "Please log in to add songs to your playlist."})
            song_id = args.get("song_id")
            download_id = args.get("download_id")
            from glconnect.models import Song, DownloadedSong, Playlist, db
            from flask_login import current_user
            if song_id:
                song = Song.query.get(song_id)
                if not song:
                    return json.dumps({"success": False, "message": "Song not found"})
                if not song.is_approved():
                    return json.dumps({"success": False, "message": "This song is not available for playlists."})
                existing = Playlist.query.filter_by(user_id=user_id, song_id=song_id).first()
                if existing:
                    return json.dumps({"success": True, "message": f"'{song.name}' is already in your playlist."})
                db.session.add(Playlist(user_id=user_id, song_id=song.id, download_id=None))
                db.session.commit()
                actions.append({"type": "add_to_playlist", "song_id": song_id, "download_id": None})
                return json.dumps({"success": True, "message": f"'{song.name}' added to your playlist!"})
            if download_id:
                d = DownloadedSong.query.get(download_id)
                if not d:
                    return json.dumps({"success": False, "message": "Song not found"})
                existing = Playlist.query.filter_by(user_id=user_id, download_id=download_id).first()
                if existing:
                    return json.dumps({"success": True, "message": f"'{d.name}' is already in your playlist."})
                db.session.add(Playlist(user_id=user_id, song_id=None, download_id=d.id))
                db.session.commit()
                actions.append({"type": "add_to_playlist", "song_id": None, "download_id": download_id})
                return json.dumps({"success": True, "message": f"'{d.name}' added to your playlist!"})
            return json.dumps({"success": False, "message": "Provide song_id or download_id"})

        if name == "list_my_playlist":
            if not user_id:
                return json.dumps({"success": False, "message": "Please log in to view your playlist."})
            from glconnect.models import Playlist, Song, Artist, DownloadedSong
            playlist = Playlist.query.filter_by(user_id=user_id).all()
            if not playlist:
                return json.dumps({"success": True, "count": 0, "songs": [], "message": "Your playlist is empty."})
            out = []
            for entry in playlist:
                if entry.song_id:
                    song = Song.query.get(entry.song_id)
                    if song:
                        artist_name = song.artist or "Unknown"
                        if song.artist_id:
                            a = Artist.query.get(song.artist_id)
                            if a:
                                artist_name = a.artist_name
                        out.append({"name": (song.name or "").strip() or "Untitled", "artist": artist_name, "song_id": song.id, "download_id": None})
                elif entry.download_id:
                    d = DownloadedSong.query.get(entry.download_id)
                    if d:
                        out.append({"name": (d.name or "").strip() or "Untitled", "artist": d.artist or "Unknown", "song_id": None, "download_id": d.id})
            return json.dumps({"success": True, "count": len(out), "songs": out})

        if name == "download_song":
            song_id = args.get("song_id")
            download_id = args.get("download_id")
            from glconnect.models import Song, DownloadedSong
            from flask import url_for
            if song_id:
                song = Song.query.get(song_id)
                if song:
                    path = url_for("playlist2.serve_song_file", song_id=song_id, _external=True)
                    fname = f"{song.artist or 'Unknown'} - {song.name or 'track'}.mp3".replace("/", "-")
                    actions.append({"type": "download", "url": path, "filename": fname})
                    return json.dumps({"success": True, "message": f"Download ready: {song.name or 'track'}"})
            if download_id:
                d = DownloadedSong.query.get(download_id)
                if d:
                    path = url_for("playlist2.serve_downloaded_song_file", download_id=download_id, _external=True)
                    fname = f"{d.artist or 'Unknown'} - {d.name or 'track'}.mp3".replace("/", "-")
                    actions.append({"type": "download", "url": path, "filename": fname})
                    return json.dumps({"success": True, "message": f"Download ready: {d.name or 'track'}"})
            return json.dumps({"success": False, "message": "Song not found"})

        return json.dumps({"error": f"Unknown tool: {name}"})

    chat = model.start_chat(history=[])
    response = chat.send_message(user_message)

    # Handle function calls in a loop
    max_iterations = 5
    for _ in range(max_iterations):
        if not response.candidates:
            break
        parts = response.candidates[0].content.parts
        has_tool_call = False
        for part in parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                name = getattr(fc, "name", None) or (fc.get("name") if isinstance(fc, dict) else None)
                args_raw = getattr(fc, "args", None) or (fc.get("args") if isinstance(fc, dict) else {})
                args = dict(args_raw) if args_raw else {}
                if not name:
                    break
                result = execute_tool(name, args)
                func_resp = genai.protos.FunctionResponse(name=name, response={"result": result})
                response = chat.send_message(
                    genai.protos.Content(parts=[genai.protos.Part(function_response=func_resp)])
                )
                has_tool_call = True
                break
        if not has_tool_call:
            break

    # Extract final text
    text = ""
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                text += part.text

    return {
        "success": True,
        "text": text.strip() or "Done.",
        "actions": actions,
    }
