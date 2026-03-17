"""
Shared playlist logic used by both manual UI (playlist2 routes) and voice/live agent.
Single source of truth for add, remove, search, play - ensures parity between manual and voice flows.
"""

from typing import Optional, Tuple, Any


def add_to_playlist_impl(
    session: Any,
    user_id: int,
    song_id: Optional[int] = None,
    download_id: Optional[int] = None,
) -> Tuple[bool, str, Optional[int]]:
    """
    Add a song to user's playlist. Same logic as manual add_to_playlist route.
    Returns (success, message, error_status_code or None).
    """
    from glconnect.models import Song, DownloadedSong, Playlist

    if song_id:
        song = session.query(Song).get(song_id)
        if not song:
            return False, "Song not found", 404
        if not song.is_approved():
            return False, "This song is not available for playlists yet.", 403
        existing = session.query(Playlist).filter_by(user_id=user_id, song_id=song_id).first()
        if existing:
            return True, f"Song is already in your playlist.", None
        session.add(Playlist(user_id=user_id, song_id=song.id, download_id=None))
        session.commit()
        return True, f"'{song.name}' added to your playlist!", None
    if download_id:
        download = session.query(DownloadedSong).get(download_id)
        if not download:
            return False, "Download not found", 404
        existing = session.query(Playlist).filter_by(user_id=user_id, download_id=download_id).first()
        if existing:
            return True, "Song is already in your playlist.", None
        session.add(Playlist(user_id=user_id, song_id=None, download_id=download.id))
        session.commit()
        return True, f"'{download.name}' added to your playlist!", None
    return False, "Provide song_id or download_id", 400


def remove_from_playlist_impl(
    session: Any,
    user_id: int,
    song_id: Optional[int] = None,
    download_id: Optional[int] = None,
) -> Tuple[bool, str, Optional[int]]:
    """
    Remove a song from user's playlist. Same logic as manual remove_song route.
    Returns (success, message, error_status_code or None).
    """
    from glconnect.models import Playlist, Song, DownloadedSong

    if song_id:
        entry = session.query(Playlist).filter_by(user_id=user_id, song_id=song_id).first()
        if not entry:
            return False, "Song not found in your playlist.", 404
        song = session.query(Song).get(song_id)
        name = song.name if song else "Song"
        session.delete(entry)
        session.commit()
        return True, f"'{name}' removed from your playlist.", None
    if download_id:
        entry = session.query(Playlist).filter_by(user_id=user_id, download_id=download_id).first()
        if not entry:
            return False, "Song not found in your playlist.", 404
        d = session.query(DownloadedSong).get(download_id)
        name = d.name if d else "Song"
        session.delete(entry)
        session.commit()
        return True, f"'{name}' removed from your playlist.", None
    return False, "Provide song_id or download_id", 400
