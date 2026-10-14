from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app
from flask_login import current_user, login_required
from glconnect.models import Song, Playlist, db, Artist, Song_upload, DownloadedSong
from glconnect.eleven_catalog import (
    eleven_songs_for_artist,
    is_artist_submission,
    is_eleven_song,
    is_public_player_song,
    list_eleven_catalog,
    resolve_eleven_file,
    suggest_eleven_catalog,
    _matches_query,
)
import os

play = Blueprint('playlist2', __name__)

# Only list songs that are approved (or legacy null); hide pending/rejected from search and playlists
def _approved_songs_filter():
    return db.or_(Song.approval_status.is_(None), Song.approval_status == 'approved')

from flask import url_for

def check_song_file_exists(song):
    """
    Check if a song file actually exists on disk using the centralized logic.
    """
    return _get_song_file_path(song) is not None

def get_all_songs_by_artist(artist_id=None, artist_name=None, include_collaborations=False):
    """GLC Radio tracks plus approved artist submissions."""
    if artist_name:
        return _songs_for_artist_name(artist_name)
    if artist_id:
        artist = Artist.query.get(artist_id)
        if artist and artist.artist_name:
            return _songs_for_artist_name(artist.artist_name)
    return list_eleven_catalog()


def _submission_rows(query=""):
    q = (query or "").strip()
    filters = [
        _approved_songs_filter(),
        db.or_(
            Song.local_path.ilike("%static/afro/%"),
            Song.local_path.ilike("%static/song_uploads/%"),
        ),
    ]
    stmt = Song.query.filter(*filters)
    if q:
        like = f"%{q}%"
        words = [word for word in q.split() if len(word) > 1]
        if len(words) > 1:
            word_filters = []
            for word in words:
                word_like = f"%{word}%"
                word_filters.append(db.or_(Song.name.ilike(word_like), Song.artist.ilike(word_like)))
            stmt = stmt.filter(db.and_(*word_filters))
        else:
            stmt = stmt.filter(db.or_(Song.name.ilike(like), Song.artist.ilike(like)))
    return [song for song in stmt.all() if is_artist_submission(song)]


def _submission_payload(song):
    cover = (song.cover_image or "").strip()
    cover_url = None
    if cover and cover != "photo3.webp" and not cover.startswith(("/", "http")):
        cover_url = f"/static/images/{cover}"
    elif cover.startswith(("/", "http")):
        cover_url = cover
    return {
        "id": song.id,
        "song_id": song.id,
        "download_id": None,
        "name": song.name or "Untitled Track",
        "artist": song.artist or "Unknown Artist",
        "path": url_for("playlist2.serve_song_file", song_id=song.id),
        "cover_image": cover_url,
        "artist_profile_pic": None,
        "filename": os.path.basename(song.local_path or ""),
        "artist_id": song.artist_id,
    }


def _merge_catalog(eleven_tracks, submissions):
    merged = list(eleven_tracks)
    seen = {track.get("song_id") for track in merged if track.get("song_id") is not None}
    for track in submissions:
        if track.get("song_id") in seen:
            continue
        seen.add(track.get("song_id"))
        merged.append(track)
    return merged


def _songs_for_artist_name(artist_name):
    name = (artist_name or "").strip().lower()
    if not name:
        return []
    tracks = eleven_songs_for_artist(artist_name)
    extra = [
        _submission_payload(song)
        for song in _submission_rows("")
        if name == (song.artist or "").strip().lower() or name in (song.artist or "").strip().lower()
    ]
    return _merge_catalog(tracks, extra)


def _all_public_tracks():
    return _merge_catalog(
        list_eleven_catalog(),
        [_submission_payload(song) for song in _submission_rows("")],
    )


def _search_public(query):
    """Title matches, plus every song by an artist whose name contains the query."""
    q = (query or "").strip().lower()
    tracks = _all_public_tracks()
    if not q:
        return []
    artist_names = set()
    if len(q) >= 2:
        for track in tracks:
            artist = (track.get("artist") or "").strip().lower()
            if artist and q in artist:
                artist_names.add(artist)
    results = []
    seen = set()
    for track in tracks:
        artist = (track.get("artist") or "").strip().lower()
        if not (_matches_query(track, query) or artist in artist_names):
            continue
        key = track.get("song_id") or track.get("path") or track.get("filename")
        if key in seen:
            continue
        seen.add(key)
        results.append(track)
    return results


def _eleven_matches(query):
    """GLC Radio originals only, used when the full catalog search cannot run."""
    return [track for track in list_eleven_catalog(sync_db=False) if _matches_query(track, query)]


@play.route('/playlist2', methods=['GET'])
def playlist2():
    """Search GLC Radio originals and approved artist submissions by title or artist."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    try:
        return jsonify(_search_public(query))
    except Exception:
        current_app.logger.exception("Music search failed for %r", query)
        try:
            return jsonify(_eleven_matches(query))
        except Exception:
            current_app.logger.exception("Music search fallback failed for %r", query)
            return jsonify([])


@play.route('/suggestions', methods=['GET'])
def get_suggestions():
    """Autocomplete across GLC Radio originals and approved artist submissions."""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'artists': [], 'songs': []})
    data = suggest_eleven_catalog(query)
    artists = list(data.get("artists") or [])
    songs = list(data.get("songs") or [])
    seen_artists = {(item.get("name") or "").strip().lower() for item in artists}
    seen_songs = {item.get("song_id") for item in songs if item.get("song_id") is not None}
    for song in _submission_rows(query):
        payload = _submission_payload(song)
        artist = (payload.get("artist") or "").strip()
        key = artist.lower()
        if artist and key not in seen_artists and len(artists) < 8:
            seen_artists.add(key)
            artists.append({"id": payload.get("artist_id"), "name": artist, "type": "artist"})
        if payload.get("song_id") not in seen_songs and len(songs) < 8:
            seen_songs.add(payload.get("song_id"))
            songs.append({
                "id": payload["id"],
                "song_id": payload["song_id"],
                "download_id": None,
                "name": payload["name"],
                "artist": artist,
                "type": "song",
            })
    return jsonify({"artists": artists, "songs": songs})


@play.route('/artist-songs', methods=['GET'])
def get_artist_songs():
    artist_name = request.args.get('artist_name', '').strip()
    artist_id = request.args.get('artist_id', type=int)
    try:
        if artist_id and not artist_name:
            artist = Artist.query.get(artist_id)
            artist_name = artist.artist_name if artist else ""
        return jsonify(_songs_for_artist_name(artist_name))
    except Exception:
        current_app.logger.exception("Artist song list failed for %r", artist_name)
        try:
            return jsonify(_eleven_matches(artist_name))
        except Exception:
            current_app.logger.exception("Artist song fallback failed for %r", artist_name)
            return jsonify([])


@play.route('/get_available_songs', methods=['GET'])
def get_available_songs():
    try:
        return jsonify(list_eleven_catalog()[:24])
    except Exception as e:
        print(f"Error fetching available songs: {e}")
        return jsonify([])


@play.route('/eleven/<path:filename>')
def serve_eleven_file(filename):
    """Serve a file from static/eleven only. Rejects path traversal."""
    file_path = resolve_eleven_file(filename)
    if not file_path:
        return jsonify({"error": "Track not found"}), 404
    return send_file(file_path, mimetype='audio/mpeg', conditional=True)


@play.route('/add_to_playlist', methods=['POST'])
@login_required
def add_to_playlist():
    from glconnect.playlist_logic import add_to_playlist_impl
    data = request.get_json()
    song_id = data.get('song_id')
    download_id = data.get('download_id')
    success, message, err_code = add_to_playlist_impl(db.session, current_user.user_id, song_id, download_id)
    if err_code:
        return jsonify({"status": "error", "message": message}), err_code
    return jsonify({"status": "success", "message": message})


# Define the function to get the user playlist
def get_user_playlist():
    user_id = current_user.user_id  # Using Flask-Login to get the current logged in user's ID
    if not user_id:
        return []  # No user is logged in, return an empty playlist

    # Fetch the user's playlist entries from the database
    playlist = Playlist.query.filter_by(user_id=user_id).all()

    # If no playlist entries are found, return an empty list
    if not playlist:
        return []

    # Prepare a list of songs from the user's playlist
    import re
    playlist_data = []
    from flask import url_for
    for entry in playlist:
        if not entry.song_id:
            continue
        if entry.song_id:
            song = Song.query.get(entry.song_id)
            if not is_public_player_song(song):
                continue
            # Get artist name - prefer artist field, fallback to artist_id lookup
            artist_name = song.artist if song.artist else 'Unknown'
            if not artist_name or artist_name == 'Unknown':
                if song.artist_id:
                    artist = Artist.query.get(song.artist_id)
                    if artist:
                        artist_name = artist.artist_name
            
            # Clean song name - handle cases where song.name contains "by [artist]" pattern
            song_name = song.name.strip() if song.name and song.name.strip() else ''
            
            # Check if song name contains "by [artist]" pattern (e.g., "by P.Square")
            by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
            if by_pattern.match(song_name):
                # Extract artist from song name if artist field is empty
                extracted_artist = by_pattern.match(song_name).group(1).strip()
                if not artist_name or artist_name == 'Unknown':
                    artist_name = extracted_artist
                song_name = ''  # Clear it since it's not actually the song name
            
            # Final song name
            if not song_name:
                song_name = 'Untitled Track'
            
            # Use the file serving route for reliable file access
            # This route handles all path resolution logic from the database
            from flask import url_for
            song_path = url_for('playlist2.serve_song_file', song_id=song.id)
            
            # Get artist profile picture if available
            artist_profile_pic = None
            if song.artist_id:
                artist_obj = Artist.query.get(song.artist_id)
                if artist_obj and artist_obj.profile_pic:
                    profile_pic_path = artist_obj.profile_pic
                    if profile_pic_path.startswith('static/'):
                        artist_profile_pic = profile_pic_path.replace('static/', '')
                    else:
                        artist_profile_pic = profile_pic_path
            
            # Get song cover image if available
            song_cover_image = song.cover_image if song.cover_image else None
            
            playlist_data.append({
                'id': song.id,
                'song_id': song.id,
                'download_id': None,
                'name': song_name,
                'artist': artist_name,
                'path': song_path,
                'cover_image': song_cover_image,
                'artist_profile_pic': artist_profile_pic
            })
    return playlist_data


@play.route('/view_playlist')
@login_required
def view_playlist():
    # Retrieve the playlist for the current logged in user
    user_playlist = get_user_playlist()
    return jsonify(user_playlist)  # Return the playlist data as JSON


@play.route('/delete_playlist', methods=['POST'])
@login_required
def delete_playlist():
    try:
        # Delete all entries from the playlist for the current user
        Playlist.query.filter_by(user_id=current_user.user_id).delete()
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Your playlist has been deleted successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error deleting playlist: {str(e)}'}), 500

@play.route('/remove_song', methods=['POST'])
@login_required
def remove_song():
    from glconnect.playlist_logic import remove_from_playlist_impl
    data = request.get_json()
    song_id = data.get('song_id')
    download_id = data.get('download_id')
    success, message, err_code = remove_from_playlist_impl(db.session, current_user.user_id, song_id, download_id)
    if err_code:
        return jsonify({"status": "error", "message": message}), err_code
    return jsonify({"status": "success", "message": message})

def _get_song_file_path(song):
    """
    Determines the absolute path of a song file.
    Returns the path if found, otherwise None.
    """
    from flask import current_app
    import logging
    logger = logging.getLogger(__name__)

    if is_eleven_song(song) and song.local_path:
        eleven_path = resolve_eleven_file(os.path.basename(song.local_path))
        if eleven_path:
            return eleven_path

    # Base directories to search for songs
    base_dirs = [
        os.path.join(current_app.root_path, 'static', 'eleven'),
        '/usr/src/appdir/glconnect/static/eleven',
        os.path.join(current_app.root_path, 'static', 'afro'),
        os.path.join(current_app.root_path, 'static', 'song_uploads'),
        '/usr/src/appdir/glconnect/static/afro',
        '/usr/src/appdir/glconnect/static/song_uploads',
    ]

    # 1. Check local_path if it's an absolute path
    if song.local_path and os.path.isabs(song.local_path):
        if os.path.exists(song.local_path):
            logger.info(f"Found song at absolute path: {song.local_path}")
            return song.local_path

    # 2. Construct filenames to check
    filenames = []
    if song.local_path:
        filenames.append(os.path.basename(song.local_path))

    artist_name = song.artist or 'Unknown'
    if song.artist_id:
        artist = Artist.query.get(song.artist_id)
        if artist:
            artist_name = artist.artist_name
    
    song_name = song.name or 'Untitled Track'
    
    # Add common filename formats
    filenames.extend([
        f"{artist_name} - {song_name}.mp3",
        f"{artist_name}-{song_name}.mp3",
        f"{song_name} - {artist_name}.mp3",
        f"{song_name}-{artist_name}.mp3",
    ])

    # Search for the file in the base directories
    for directory in base_dirs:
        for filename in filenames:
            if not filename: continue
            file_path = os.path.join(directory, filename)
            if os.path.exists(file_path):
                logger.info(f"Found song at: {file_path}")
                return file_path

    logger.warning(f"Song file not found for song_id={song.id}, name='{song.name}'")
    return None

@play.route('/song/<int:song_id>/file')
def serve_song_file(song_id):
    """Serve song file by ID (Song table / artist uploads)."""
    try:
        song = Song.query.get_or_404(song_id)
        if not is_public_player_song(song):
            return jsonify({"error": "This song is not available in the player"}), 404
        file_path = _get_song_file_path(song)

        if file_path:
            return send_file(file_path, mimetype='audio/mpeg')
        else:
            # Log detailed error information
            from flask import current_app
            error_info = {
                "song_id": song_id,
                "song_name": song.name,
                "artist": song.artist,
                "local_path": song.local_path,
                "app_root": current_app.root_path,
                "cwd": os.getcwd(),
            }
            current_app.logger.error(f"Song file not found. Details: {error_info}")
            return jsonify({"error": "Song file not found", "details": error_info}), 404
            
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error serving song file: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


def _get_downloaded_song_file_path(download):
    """
    Determines the absolute path of a downloaded song file.
    Returns the path if found, otherwise None.
    """
    from flask import current_app
    import logging
    logger = logging.getLogger(__name__)

    if not download.local_path:
        return None

    # Base directories to search for downloaded songs
    base_dirs = [
        os.path.join(current_app.root_path, 'static', 'ytauto'),
        '/usr/src/appdir/glconnect/static/ytauto',
    ]

    filename = os.path.basename(download.local_path)

    # Search for the file in the base directories
    for directory in base_dirs:
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            logger.info(f"Found downloaded song at: {file_path}")
            return file_path

    logger.warning(f"Downloaded song file not found for download_id={download.id}, name='{download.name}'")
    return None

@play.route('/download/<int:download_id>/file')
def serve_downloaded_song_file(download_id):
    """Serve a YouTube-downloaded song file by download_id."""
    try:
        download = DownloadedSong.query.get_or_404(download_id)
        file_path = _get_downloaded_song_file_path(download)

        if file_path:
            return send_file(file_path, mimetype='audio/mpeg')
        else:
            from flask import current_app
            error_info = {
                "download_id": download_id,
                "download_name": download.name,
                "local_path": download.local_path,
                "app_root": current_app.root_path,
                "cwd": os.getcwd(),
            }
            current_app.logger.error(f"Downloaded song file not found. Details: {error_info}")
            return jsonify({"error": "Downloaded song file not found", "details": error_info}), 404

    except Exception as e:
        import traceback
        from flask import current_app
        current_app.logger.error(f"Error serving downloaded song file: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
