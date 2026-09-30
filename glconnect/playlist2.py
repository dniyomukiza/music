from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app
from flask_login import current_user, login_required
from glconnect.models import Song, Playlist, db, Artist, Song_upload, DownloadedSong
from glconnect.eleven_catalog import (
    eleven_songs_for_artist,
    is_eleven_song,
    list_eleven_catalog,
    resolve_eleven_file,
    search_eleven_catalog,
    suggest_eleven_catalog,
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
    """Return ElevenLabs / GLC Radio tracks only. Other folders are excluded from search."""
    if artist_name:
        return eleven_songs_for_artist(artist_name)
    return list_eleven_catalog()


@play.route('/playlist2', methods=['GET'])
def playlist2():
    """Search only ElevenLabs / GLC Radio originals under static/eleven."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    return jsonify(search_eleven_catalog(query))


@play.route('/suggestions', methods=['GET'])
def get_suggestions():
    """Autocomplete from the ElevenLabs catalog only."""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'artists': [], 'songs': []})
    return jsonify(suggest_eleven_catalog(query))


@play.route('/artist-songs', methods=['GET'])
def get_artist_songs():
    artist_name = request.args.get('artist_name', '').strip()
    return jsonify(eleven_songs_for_artist(artist_name))


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
            if not song or not is_eleven_song(song):
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
        if not is_eleven_song(song):
            return jsonify({"error": "Only GLC Radio originals are available in the player"}), 404
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
