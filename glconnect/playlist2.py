from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app
from flask_login import current_user, login_required
from glconnect.models import Song, Playlist, db, Artist, Song_upload
import os

play = Blueprint('playlist2', __name__)

from flask import url_for

def check_song_file_exists(song):
    """
    Check if a song file actually exists on disk.
    Uses the same path resolution logic as serve_song_file.
    Returns True if file exists, False otherwise.
    """
    try:
        from flask import current_app
        app_root = current_app.root_path if hasattr(current_app, 'root_path') else os.getcwd()
        
        # If app_root is already in glconnect directory, go up one level
        if os.path.basename(app_root) == 'glconnect':
            project_root = os.path.dirname(app_root)
        else:
            project_root = app_root
        
        # Define possible directories to search
        possible_dirs = []
        glconnect_static_afro = os.path.join(project_root, 'glconnect', 'static', 'afro')
        cwd_glconnect_afro = os.path.join(os.getcwd(), 'glconnect', 'static', 'afro')
        
        possible_dirs.extend([
            glconnect_static_afro,
            cwd_glconnect_afro,
            os.path.join(project_root, 'static', 'afro'),
            os.path.join(os.getcwd(), 'glconnect', 'static', 'afro'),
            'glconnect/static/afro',
            'static/afro',
        ])
        
        # Filter to only existing directories
        existing_dirs = [d for d in possible_dirs if os.path.exists(d) and os.path.isdir(d)]
        if existing_dirs:
            possible_dirs = existing_dirs + [d for d in possible_dirs if d not in existing_dirs]
        
        filename = None
        
        # Try to find the file using local_path if available
        if song.local_path:
            if os.path.isabs(song.local_path) and os.path.exists(song.local_path):
                return True
            
            if '/' not in song.local_path and '\\' not in song.local_path:
                filename = song.local_path
                for base_dir in [glconnect_static_afro, cwd_glconnect_afro]:
                    if os.path.exists(base_dir):
                        file_path = os.path.join(base_dir, filename)
                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            return True
            
            if '/' in song.local_path or '\\' in song.local_path:
                filename = os.path.basename(song.local_path)
            else:
                filename = song.local_path
            
            # Search for the file in all possible directories
            for directory in possible_dirs:
                if not directory:
                    continue
                file_path = os.path.join(directory, filename) if os.path.isabs(directory) or os.path.sep in directory else os.path.join(project_root, directory, filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    return True
        
        # Fallback: try constructed path
        import re
        artist_name = song.artist if song.artist else 'Unknown'
        song_name_for_path = song.name if song.name else 'Untitled Track'
        
        # Check if song.name contains "by [artist]" pattern
        by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
        if by_pattern.match(song_name_for_path):
            extracted_artist = by_pattern.match(song_name_for_path).group(1).strip()
            if not artist_name or artist_name == 'Unknown':
                artist_name = extracted_artist
            song_name_for_path = 'Untitled Track'
        
        if song.artist_id:
            artist_obj = Artist.query.get(song.artist_id)
            if artist_obj:
                artist_name = artist_obj.artist_name
        
        # Try multiple constructed filename formats
        constructed_filenames = [
            f"{artist_name} - {song_name_for_path}.mp3",
            f"{artist_name}-{song_name_for_path}.mp3",
            f"{song_name_for_path} - {artist_name}.mp3",
            f"{song_name_for_path}-{artist_name}.mp3",
        ]
        
        from werkzeug.utils import secure_filename
        secure_base = secure_filename(f"{artist_name} - {song_name_for_path}")
        constructed_filenames.append(f"{secure_base}.mp3")
        
        # Also try with common video suffixes (in case filename has them but DB doesn't)
        video_suffixes = [
            " (Official Lyric Video)",
            " (Lyric Video)",
            " (Official Video)",
            " (Video)",
        ]
        for suffix in video_suffixes:
            constructed_filenames.append(f"{artist_name} - {song_name_for_path}{suffix}.mp3")
            constructed_filenames.append(f"{artist_name}-{song_name_for_path}{suffix}.mp3")
        
        # Try exact match first (if local_path is set)
        if song.local_path:
            for directory in possible_dirs:
                if not directory:
                    continue
                exact_path = os.path.join(directory, song.local_path) if os.path.isabs(directory) or os.path.sep in directory else os.path.join(project_root, directory, song.local_path)
                if os.path.exists(exact_path) and os.path.isfile(exact_path):
                    return True
        
        # Try all constructed filenames
        for constructed_filename in constructed_filenames:
            for directory in possible_dirs:
                if not directory:
                    continue
                file_path = os.path.join(directory, constructed_filename) if os.path.isabs(directory) or os.path.sep in directory else os.path.join(project_root, directory, constructed_filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    return True
        
        # Last resort: search all files in directory and match by normalized name
        import re
        normalized_artist = re.sub(r'[^a-z0-9]', '', artist_name.lower()) if artist_name else ""
        normalized_song = re.sub(r'[^a-z0-9]', '', song_name_for_path.lower())
        
        for directory in possible_dirs:
            if not directory or not os.path.exists(directory):
                continue
            try:
                for file in os.listdir(directory):
                    if not file.lower().endswith('.mp3'):
                        continue
                    # Normalize filename for comparison
                    file_base = file.replace('.mp3', '').lower()
                    # Remove common suffixes
                    file_base = re.sub(r'\s*\([^)]*\)\s*', '', file_base)
                    file_normalized = re.sub(r'[^a-z0-9]', '', file_base)
                    
                    # Check if normalized artist and song match
                    if normalized_artist and normalized_song:
                        if normalized_artist in file_normalized and normalized_song in file_normalized:
                            return True
            except Exception:
                continue
        
        return False
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error checking if song file exists for song {song.id}: {e}")
        return False

def get_all_songs_by_artist(artist_id=None, artist_name=None):
    """
    Get all songs by an artist from Song model (playlist-compatible songs).
    Note: Song_upload songs are not included as they can't be added to playlists directly.
    Returns a list of song dictionaries with id, name, and artist fields.
    """
    songs_data = []
    
    # Get songs from Song model
    if artist_id:
        songs_from_song_model = Song.query.filter_by(artist_id=artist_id).all()
    elif artist_name:
        # Try to find artist by name first
        artist = Artist.query.filter(db.func.lower(Artist.artist_name) == artist_name.lower()).first()
        if artist:
            songs_from_song_model = Song.query.filter_by(artist_id=artist.artist_id).all()
        else:
            # Fallback: search by artist field in Song model
            songs_from_song_model = Song.query.filter(db.func.lower(Song.artist) == artist_name.lower()).all()
    else:
        songs_from_song_model = []
    
    # Process songs from Song model (only these can be added to playlists)
    import re
    for song in songs_from_song_model:
        artist_name_display = song.artist if song.artist else 'Unknown'
        if not artist_name_display or artist_name_display == 'Unknown':
            if song.artist_id:
                artist_obj = Artist.query.get(song.artist_id)
                if artist_obj:
                    artist_name_display = artist_obj.artist_name
        
        # Clean song name - handle cases where song.name contains "by [artist]" pattern
        song_name = song.name.strip() if song.name and song.name.strip() else ''
        
        # Check if song name contains "by [artist]" pattern (e.g., "by P.Square")
        by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
        if by_pattern.match(song_name):
            # Extract artist from song name if artist field is empty
            extracted_artist = by_pattern.match(song_name).group(1).strip()
            if not artist_name_display or artist_name_display == 'Unknown':
                artist_name_display = extracted_artist
            song_name = ''  # Clear it since it's not actually the song name
        
        # Final song name
        if not song_name:
            song_name = 'Untitled Track'
        
        # Check if song file actually exists before including it
        if not check_song_file_exists(song):
            continue  # Skip songs without playable files
        
        # Use the file serving route for reliable file access
        # This route handles all path resolution logic from the database
        from flask import url_for
        song_path = url_for('playlist2.serve_song_file', song_id=song.id)
        
        songs_data.append({
            'id': song.id,
            'name': song_name,
            'artist': artist_name_display,
            'path': song_path  # Use the file serving route
        })
    
    return songs_data

# In your route for fetching songs
@play.route('/playlist2', methods=['GET'])
def playlist2():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])

    # 1. Exact match for artist (case-insensitive) - return all songs by that artist
    artist = Artist.query.filter(db.func.lower(Artist.artist_name) == query).first()
    if artist:
        songs_data = get_all_songs_by_artist(artist_id=artist.artist_id, artist_name=artist.artist_name)
        if songs_data:
            return jsonify(songs_data)
        # If no songs found, still return empty array (don't redirect)

    # 2. Search for songs matching the query (partial match for song name)
    songs = Song.query.filter(db.func.lower(Song.name).like(f'%{query}%')).limit(20).all()
    
    if songs:
        # If we found songs, get the artist from the first song and return ALL songs by that artist
        first_song = songs[0]
        artist_id = first_song.artist_id
        artist_name = first_song.artist
        
        # Get artist name if we have artist_id
        if artist_id:
            artist_obj = Artist.query.get(artist_id)
            if artist_obj:
                artist_name = artist_obj.artist_name
        
        # If we don't have artist_name yet, try to get it from the song
        if not artist_name or artist_name == 'Unknown':
            artist_name = first_song.artist if first_song.artist else None
        
        # Get all songs by this artist
        if artist_id or artist_name:
            songs_data = get_all_songs_by_artist(artist_id=artist_id, artist_name=artist_name)
            if songs_data:
                return jsonify(songs_data)
        
        # Fallback: return the songs we found (original behavior)
        import re
        songs_data = []
        for song in songs:
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
            
            # Check if song file actually exists before including it
            if not check_song_file_exists(song):
                continue  # Skip songs without playable files
            
            # Use the file serving route for reliable file access
            from flask import url_for
            song_path = url_for('playlist2.serve_song_file', song_id=song.id)
            
            songs_data.append({
                'id': song.id,
                'name': song_name,
                'artist': artist_name,
                'path': song_path
            })
        return jsonify(songs_data)
    
    # 3. Search Song.artist field directly FIRST (for collaborations like "Artist ft Diamond Platnumz")
    # This catches all songs where the artist field contains the query, even if not in Artist table
    songs_by_artist_field = Song.query.filter(db.func.lower(Song.artist).like(f'%{query}%')).all()
    if songs_by_artist_field:
        # Group by artist to return all songs by matching artists
        artist_groups = {}
        for song in songs_by_artist_field:
            artist_name = song.artist if song.artist else 'Unknown'
            if artist_name not in artist_groups:
                artist_groups[artist_name] = []
            artist_groups[artist_name].append(song)
        
        # Return all songs from all matching artists
        import re
        songs_data = []
        for artist_name, artist_songs in artist_groups.items():
            for song in artist_songs:
                # Clean song name
                song_name = song.name.strip() if song.name and song.name.strip() else ''
                by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
                if by_pattern.match(song_name):
                    extracted_artist = by_pattern.match(song_name).group(1).strip()
                    if not artist_name or artist_name == 'Unknown':
                        artist_name = extracted_artist
                    song_name = ''
                
                if not song_name:
                    song_name = 'Untitled Track'
                
                # Include all songs from database, even if file doesn't exist
                # (File existence will be checked when trying to play)
                from flask import url_for
                song_path = url_for('playlist2.serve_song_file', song_id=song.id)
                
                songs_data.append({
                    'id': song.id,
                    'name': song_name,
                    'artist': artist_name,
                    'path': song_path
                })
        
        if songs_data:
            return jsonify(songs_data)
    
    # 3b. Partial match for artist name in Artist table (fallback if Song.artist search found nothing)
    artist_partial = Artist.query.filter(db.func.lower(Artist.artist_name).like(f'%{query}%')).first()
    if artist_partial:
        songs_data = get_all_songs_by_artist(artist_id=artist_partial.artist_id, artist_name=artist_partial.artist_name)
        if songs_data:
            return jsonify(songs_data)

    # 4. Exact match for song name (if no partial matches)
    song = Song.query.filter(db.func.lower(Song.name) == query).first()
    if song:
        artist_id = song.artist_id
        artist_name = song.artist
        
        # Get artist name if we have artist_id
        if artist_id:
            artist_obj = Artist.query.get(artist_id)
            if artist_obj:
                artist_name = artist_obj.artist_name
        
        # Get all songs by this artist
        if artist_id or artist_name:
            songs_data = get_all_songs_by_artist(artist_id=artist_id, artist_name=artist_name)
            if songs_data:
                return jsonify(songs_data)

    # No match found
    return jsonify([])

@play.route('/get_available_songs', methods=['GET'])
def get_available_songs():
    """Get list of available songs for display"""
    try:
        from flask import url_for
        import re
        # Get a limited number of songs (e.g., 12 most recent or popular)
        songs = Song.query.order_by(Song.id.desc()).limit(12).all()
        
        songs_data = []
        for song in songs:
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
            
            # Check if song file actually exists before including it
            if not check_song_file_exists(song):
                continue  # Skip songs without playable files
            
            # Use the file serving route for reliable file access
            # This route handles all path resolution logic
            song_path = url_for('playlist2.serve_song_file', song_id=song.id)
            
            songs_data.append({
                'id': song.id,
                'name': song_name,
                'artist': artist_name,
                'path': song_path
            })
        
        return jsonify(songs_data)
    except Exception as e:
        print(f"Error fetching available songs: {e}")
        return jsonify([])



@play.route('/add_to_playlist', methods=['POST'])
@login_required
def add_to_playlist():
    print("Authenticated?", current_user.is_authenticated)
    print("User ID?", getattr(current_user, 'user_id', 'NO user_id'))
    print("User Object?", current_user)
    data = request.get_json()
    song_id = data.get('song_id')

    if not song_id:
        return jsonify({"status": "error", "message": "Invalid song ID"}), 400

    song = Song.query.get(song_id)
    if not song:
        return jsonify({"status": "error", "message": "Song not found"}), 404

    # Check if the song is already in the user's playlist
    existing_entry = Playlist.query.filter_by(user_id=current_user.user_id, song_id=song_id).first()
    if existing_entry:
        return jsonify({"status": "success", "message": "Song is already in your playlist."})
    
    # Add song to user's playlist
    new_playlist_entry = Playlist(user_id=current_user.user_id, song_id=song.id)
    db.session.add(new_playlist_entry)
    db.session.commit()

    return jsonify({"status": "success", "message": f"'{song.name}' added to your playlist!"})


# Define the function to get the user playlist
def get_user_playlist():
    user_id = current_user.user_id  # Using Flask-Login to get the current logged-in user's ID
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
    for entry in playlist:
        song = Song.query.get(entry.song_id)
        if song:
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
            
            playlist_data.append({
                'id': song.id,
                'name': song_name,
                'artist': artist_name,
                'path': song_path  # Use the file serving route
            })
    
    return playlist_data


@play.route('/view_playlist')
@login_required
def view_playlist():
    # Retrieve the playlist for the current logged-in user
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
    data = request.get_json()
    song_id = data.get('song_id')

    if not song_id:
        return jsonify({"status": "error", "message": "Invalid song ID"}), 400

    song = Song.query.get(song_id)
    if not song:
        return jsonify({"status": "error", "message": "Song not found"}), 404

    # Check if the song is in the user's playlist
    playlist_entry = Playlist.query.filter_by(user_id=current_user.user_id, song_id=song_id).first()
    if not playlist_entry:
        return jsonify({"status": "error", "message": "Song not found in your playlist."}), 404

    # Remove the song from the playlist
    db.session.delete(playlist_entry)
    db.session.commit()

    return jsonify({"status": "success", "message": f"'{song.name}' removed from your playlist!"})

@play.route('/song/<int:song_id>/file')
def serve_song_file(song_id):
    """Serve song file by ID - handles file lookup and path resolution"""
    try:
        from flask import current_app, request
        import logging
        logger = logging.getLogger(__name__)
        
        song = Song.query.get_or_404(song_id)
        
        # Get the Flask app root path for reliable path resolution
        app_root = current_app.root_path if hasattr(current_app, 'root_path') else os.getcwd()
        
        # If app_root is already in glconnect directory, go up one level
        if os.path.basename(app_root) == 'glconnect':
            project_root = os.path.dirname(app_root)
        else:
            project_root = app_root
        
        # Define possible directories to search - prioritize actual existing paths
        possible_dirs = []
        
        # Try to find glconnect directory relative to project root
        glconnect_static_afro = os.path.join(project_root, 'glconnect', 'static', 'afro')
        
        # Also try with current working directory
        cwd_glconnect_afro = os.path.join(os.getcwd(), 'glconnect', 'static', 'afro')
        
        # Add all possible directory locations - prioritize existing directories
        possible_dirs.extend([
            glconnect_static_afro,
            cwd_glconnect_afro,
            os.path.join(project_root, 'static', 'afro'),
            os.path.join(os.getcwd(), 'glconnect', 'static', 'afro'),
        ])
        
        # Add relative paths as fallback
        possible_dirs.extend([
            'glconnect/static/afro',
            'static/afro',
            '/usr/src/appdir/glconnect/static/afro',
            '/liqfolder/glconnect/static/afro',
        ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_dirs = []
        for d in possible_dirs:
            if d not in seen:
                seen.add(d)
                unique_dirs.append(d)
        possible_dirs = unique_dirs
        
        # Filter to only existing directories for faster lookup
        existing_dirs = [d for d in possible_dirs if os.path.exists(d) and os.path.isdir(d)]
        if existing_dirs:
            possible_dirs = existing_dirs + [d for d in possible_dirs if d not in existing_dirs]
        
        # Initialize filename variable
        filename = None
        
        # Try to find the file using local_path if available
        if song.local_path:
            # First, check if local_path is an absolute path that exists
            if os.path.isabs(song.local_path) and os.path.exists(song.local_path):
                logger.info(f"Found song file via absolute path: {song.local_path}")
                return send_file(song.local_path, mimetype='audio/mpeg')
            
            # If local_path is just a filename (no slashes), try afro directory
            if '/' not in song.local_path and '\\' not in song.local_path:
                filename = song.local_path
                # Try afro directory
                for base_dir in [glconnect_static_afro, cwd_glconnect_afro]:
                    if os.path.exists(base_dir):
                        file_path = os.path.join(base_dir, filename)
                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            logger.info(f"Found song file: {file_path}")
                            return send_file(file_path, mimetype='audio/mpeg')
            
            # If it's an absolute path that doesn't exist, try to map it to current environment
            # Handle paths like /liqfolder/glconnect/static/afro/filename.mp3
            if os.path.isabs(song.local_path):
                # Extract the relative part after the base directory
                path_parts = song.local_path.strip('/').split('/')
                # Find 'glconnect' or 'static' in the path and reconstruct from there
                if 'glconnect' in path_parts:
                    glconnect_idx = path_parts.index('glconnect')
                    relative_path = '/'.join(path_parts[glconnect_idx:])
                    # Try with project_root (not app_root, which might be in glconnect/)
                    reconstructed_path = os.path.join(project_root, relative_path)
                    if os.path.exists(reconstructed_path) and os.path.isfile(reconstructed_path):
                        logger.info(f"Found song file via reconstructed path: {reconstructed_path}")
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
                    # Try with cwd
                    reconstructed_path = os.path.join(os.getcwd(), relative_path)
                    if os.path.exists(reconstructed_path) and os.path.isfile(reconstructed_path):
                        logger.info(f"Found song file via reconstructed path: {reconstructed_path}")
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
                elif 'static' in path_parts:
                    static_idx = path_parts.index('static')
                    relative_path = '/'.join(path_parts[static_idx:])
                    # Try with glconnect prefix using project_root
                    reconstructed_path = os.path.join(project_root, 'glconnect', relative_path)
                    if os.path.exists(reconstructed_path) and os.path.isfile(reconstructed_path):
                        logger.info(f"Found song file via reconstructed path: {reconstructed_path}")
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
                    # Try without glconnect prefix
                    reconstructed_path = os.path.join(project_root, relative_path)
                    if os.path.exists(reconstructed_path) and os.path.isfile(reconstructed_path):
                        logger.info(f"Found song file via reconstructed path: {reconstructed_path}")
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
                
                # If reconstruction failed, extract just the filename and search in possible_dirs
                filename = os.path.basename(song.local_path)
            
            # Extract filename if not already set
            if 'filename' not in locals() or not filename:
                if '/' in song.local_path or '\\' in song.local_path:
                    filename = os.path.basename(song.local_path)
                else:
                    filename = song.local_path
                # Extract filename from path (handles both absolute and relative paths)
                if '/' in song.local_path or '\\' in song.local_path:
                    filename = os.path.basename(song.local_path)
                else:
                    filename = song.local_path
            
            # Also try the directory from the stored path if it's a relative path
            if '/' in song.local_path and not os.path.isabs(song.local_path):
                # Extract directory from relative path like "static/afro/filename.mp3"
                path_parts = song.local_path.split('/')
                if len(path_parts) > 1:
                    # Reconstruct relative directory path
                    relative_dir = '/'.join(path_parts[:-1])
                    # Add to beginning of possible_dirs
                    possible_dirs.insert(0, os.path.join(project_root, relative_dir))
                    possible_dirs.insert(0, os.path.join(project_root, 'glconnect', relative_dir))
                    if not relative_dir.startswith('glconnect/'):
                        possible_dirs.insert(0, f"glconnect/{relative_dir}")
                    possible_dirs.insert(0, relative_dir)
            
            # Search for the file in all possible directories
            for directory in possible_dirs:
                if not directory:
                    continue
                file_path = os.path.join(directory, filename) if os.path.isabs(directory) or os.path.sep in directory else os.path.join(project_root, directory, filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    return send_file(file_path, mimetype='audio/mpeg')
            
            # If local_path contains a directory structure, try reconstructing it
            if '/' in song.local_path and not os.path.isabs(song.local_path):
                # Try to find the file by reconstructing the path relative to project root
                reconstructed_path = os.path.join(project_root, song.local_path.lstrip('/'))
                if os.path.exists(reconstructed_path) and os.path.isfile(reconstructed_path):
                    return send_file(reconstructed_path, mimetype='audio/mpeg')
                
                # Try with glconnect prefix
                if not song.local_path.startswith('glconnect/'):
                    reconstructed_path = os.path.join(project_root, 'glconnect', song.local_path.lstrip('/'))
                    if os.path.exists(reconstructed_path) and os.path.isfile(reconstructed_path):
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
        
        # Fallback: try constructed path
        # Get artist name - handle "by [artist]" pattern in song name
        import re
        artist_name = song.artist if song.artist else 'Unknown'
        song_name_for_path = song.name if song.name else 'Untitled Track'
        
        # Check if song.name contains "by [artist]" pattern
        by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
        if by_pattern.match(song_name_for_path):
            # Extract artist from song name
            extracted_artist = by_pattern.match(song_name_for_path).group(1).strip()
            if not artist_name or artist_name == 'Unknown':
                artist_name = extracted_artist
            song_name_for_path = 'Untitled Track'  # Clear it since it's not actually the song name
        
        if song.artist_id:
            artist_obj = Artist.query.get(song.artist_id)
            if artist_obj:
                artist_name = artist_obj.artist_name
        
        # Try multiple constructed filename formats
        constructed_filenames = [
            f"{artist_name} - {song_name_for_path}.mp3",
            f"{artist_name}-{song_name_for_path}.mp3",
            f"{song_name_for_path} - {artist_name}.mp3",
            f"{song_name_for_path}-{artist_name}.mp3",
        ]
        
        # Also try with secure_filename format (used during upload)
        from werkzeug.utils import secure_filename
        secure_base = secure_filename(f"{artist_name} - {song_name_for_path}")
        constructed_filenames.append(f"{secure_base}.mp3")
        
        for constructed_filename in constructed_filenames:
            for directory in possible_dirs:
                if not directory:
                    continue
                file_path = os.path.join(directory, constructed_filename) if os.path.isabs(directory) or os.path.sep in directory else os.path.join(project_root, directory, constructed_filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    logger.info(f"Found song file via constructed path: {file_path}")
                    return send_file(file_path, mimetype='audio/mpeg')
        
        # If still not found, try searching for similar filenames (case-insensitive)
        song_name_lower = song.name.lower() if song.name else ''
        artist_name_lower = artist_name.lower() if artist_name != 'Unknown' else ''
        
        # Also try searching by song ID in filename (some systems use IDs)
        for directory in possible_dirs:
            if not directory or not os.path.exists(directory):
                continue
            try:
                for file in os.listdir(directory):
                    file_lower = file.lower()
                    # Check multiple matching strategies
                    matches = False
                    if file.endswith('.mp3'):
                        # Strategy 1: Contains song name or artist name
                        if (song_name_lower and song_name_lower in file_lower) or (artist_name_lower and artist_name_lower in file_lower):
                            matches = True
                        # Strategy 2: Contains song ID
                        elif str(song_id) in file or f"_{song_id}." in file_lower or f"-{song_id}." in file_lower:
                            matches = True
                        # Strategy 3: If we have a filename from local_path, try exact match (case-insensitive)
                        elif filename and file_lower == filename.lower():
                            matches = True
                    
                    if matches:
                        file_path = os.path.join(directory, file)
                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            logger.info(f"Found song file via search: {file_path}")
                            return send_file(file_path, mimetype='audio/mpeg')
            except (OSError, PermissionError) as e:
                # Skip directories we can't read
                logger.warning(f"Cannot read directory {directory}: {e}")
                continue
        
        # Last resort: Try using Flask's static file serving mechanism
        # Construct relative path from static folder
        static_relative_paths = [
            f"afro/{constructed_filename}",
            f"afro/{filename}" if 'filename' in locals() and filename else None,
        ]
        
        for static_path in static_relative_paths:
            if not static_path:
                continue
            try:
                # Try with glconnect/static prefix
                glconnect_static = os.path.join(project_root, 'glconnect', 'static')
                if os.path.exists(glconnect_static):
                    full_path = os.path.join(glconnect_static, static_path)
                    if os.path.exists(full_path) and os.path.isfile(full_path):
                        # Extract the directory and filename for send_from_directory
                        static_dir = os.path.dirname(full_path)
                        static_filename = os.path.basename(full_path)
                        return send_from_directory(static_dir, static_filename, mimetype='audio/mpeg')
            except Exception:
                continue
        
        # Last resort: Comprehensive directory scan - try to find ANY mp3 file that might match
        # This is useful when filenames don't match exactly but files exist
        for directory in existing_dirs if 'existing_dirs' in locals() else possible_dirs:
            if not directory or not os.path.exists(directory):
                continue
            try:
                for file in os.listdir(directory):
                    if not file.endswith('.mp3'):
                        continue
                    file_lower = file.lower()
                    file_path = os.path.join(directory, file)
                    
                    # Very loose matching - if any part of song name or artist appears in filename
                    if song_name_for_path and song_name_for_path.lower() in file_lower:
                        logger.info(f"Found song file via loose name match: {file_path}")
                        return send_file(file_path, mimetype='audio/mpeg')
                    if artist_name and artist_name.lower() != 'unknown' and artist_name.lower() in file_lower:
                        logger.info(f"Found song file via loose artist match: {file_path}")
                        return send_file(file_path, mimetype='audio/mpeg')
            except (OSError, PermissionError) as e:
                logger.warning(f"Cannot read directory {directory}: {e}")
                continue
        
        # Last resort: return a more detailed error message
        error_info = {
            "song_id": song_id,
            "song_name": song.name,
            "artist": artist_name,
            "local_path": song.local_path,
            "constructed_filenames": constructed_filenames if 'constructed_filenames' in locals() else [f"{artist_name} - {song_name_for_path}.mp3"],
            "app_root": app_root,
            "cwd": os.getcwd(),
            "searched_directories": [d for d in possible_dirs if os.path.exists(d)][:5]  # First 5 existing dirs
        }
        logger.error(f"Song file not found for song_id={song_id}: {error_info}")
        return jsonify({"error": "Song file not found", "details": error_info}), 404
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
