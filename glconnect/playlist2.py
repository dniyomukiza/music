from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app
from flask_login import current_user, login_required
from glconnect.models import Song, Playlist, db, Artist, Song_upload
import os

play = Blueprint('playlist2', __name__)

from flask import url_for

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
            
            # Use local_path if available (same logic as template routes)
            if song.local_path:
                import os
                if '/' in song.local_path or '\\' in song.local_path:
                    filename = os.path.basename(song.local_path)
                    # Remove any directory prefixes
                    if '/' in filename:
                        filename = filename.split('/')[-1]
                    if '\\' in filename:
                        filename = filename.split('\\')[-1]
                    song_path = f"/static/afro/{filename}"
                else:
                    # It's already a relative path or filename
                    if song.local_path.startswith('/'):
                        song_path = song.local_path
                    elif song.local_path.startswith('static/'):
                        song_path = f"/{song.local_path}"
                    else:
                        song_path = f"/static/afro/{song.local_path}"
            else:
                # Fallback to constructed path
                import urllib.parse
                song_path = f"/static/afro/{urllib.parse.quote(artist_name)} - {urllib.parse.quote(song_name)}.mp3"
            
            songs_data.append({
                'id': song.id,
                'name': song_name,
                'artist': artist_name,
                'path': song_path
            })
        return jsonify(songs_data)
    
    # 3. Partial match for artist name (if no songs found)
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
        from flask import current_app
        song = Song.query.get_or_404(song_id)
        
        # Get the Flask app root path for reliable path resolution
        app_root = current_app.root_path if hasattr(current_app, 'root_path') else os.getcwd()
        
        # Define possible directories to search - prioritize actual existing paths
        possible_dirs = []
        
        # Try to find glconnect directory relative to app root
        glconnect_static_afro = os.path.join(app_root, 'glconnect', 'static', 'afro')
        glconnect_static_uploads = os.path.join(app_root, 'glconnect', 'static', 'song_uploads')
        
        # Add all possible directory locations
        possible_dirs.extend([
            glconnect_static_afro,
            glconnect_static_uploads,
            os.path.join(app_root, 'static', 'afro'),
            os.path.join(app_root, 'static', 'song_uploads'),
            os.path.join(os.getcwd(), 'glconnect', 'static', 'afro'),
            os.path.join(os.getcwd(), 'glconnect', 'static', 'song_uploads'),
            'glconnect/static/afro',
            'glconnect/static/song_uploads',
            'static/afro',
            'static/song_uploads',
            '/usr/src/appdir/glconnect/static/afro',
            '/usr/src/appdir/glconnect/static/song_uploads',
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
        
        # Initialize filename variable
        filename = None
        
        # Try to find the file using local_path if available
        if song.local_path:
            # First, check if local_path is an absolute path that exists
            if os.path.isabs(song.local_path) and os.path.exists(song.local_path):
                return send_file(song.local_path, mimetype='audio/mpeg')
            
            # If it's an absolute path that doesn't exist, try to map it to current environment
            # Handle paths like /liqfolder/glconnect/static/afro/filename.mp3
            if os.path.isabs(song.local_path):
                # Extract the relative part after the base directory
                path_parts = song.local_path.strip('/').split('/')
                # Find 'glconnect' or 'static' in the path and reconstruct from there
                if 'glconnect' in path_parts:
                    glconnect_idx = path_parts.index('glconnect')
                    relative_path = '/'.join(path_parts[glconnect_idx:])
                    # Try with app_root
                    reconstructed_path = os.path.join(app_root, relative_path)
                    if os.path.exists(reconstructed_path):
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
                    # Try with cwd
                    reconstructed_path = os.path.join(os.getcwd(), relative_path)
                    if os.path.exists(reconstructed_path):
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
                elif 'static' in path_parts:
                    static_idx = path_parts.index('static')
                    relative_path = '/'.join(path_parts[static_idx:])
                    # Try with glconnect prefix
                    reconstructed_path = os.path.join(app_root, 'glconnect', relative_path)
                    if os.path.exists(reconstructed_path):
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
                    # Try without glconnect prefix
                    reconstructed_path = os.path.join(app_root, relative_path)
                    if os.path.exists(reconstructed_path):
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
            
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
                    possible_dirs.insert(0, os.path.join(app_root, relative_dir))
                    possible_dirs.insert(0, os.path.join(app_root, 'glconnect', relative_dir))
                    if not relative_dir.startswith('glconnect/'):
                        possible_dirs.insert(0, f"glconnect/{relative_dir}")
                    possible_dirs.insert(0, relative_dir)
            
            # Search for the file in all possible directories
            for directory in possible_dirs:
                if not directory:
                    continue
                file_path = os.path.join(directory, filename) if os.path.isabs(directory) or os.path.sep in directory else os.path.join(app_root, directory, filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    return send_file(file_path, mimetype='audio/mpeg')
            
            # If local_path contains a directory structure, try reconstructing it
            if '/' in song.local_path and not os.path.isabs(song.local_path):
                # Try to find the file by reconstructing the path relative to app root
                reconstructed_path = os.path.join(app_root, song.local_path.lstrip('/'))
                if os.path.exists(reconstructed_path) and os.path.isfile(reconstructed_path):
                    return send_file(reconstructed_path, mimetype='audio/mpeg')
                
                # Try with glconnect prefix
                if not song.local_path.startswith('glconnect/'):
                    reconstructed_path = os.path.join(app_root, 'glconnect', song.local_path.lstrip('/'))
                    if os.path.exists(reconstructed_path) and os.path.isfile(reconstructed_path):
                        return send_file(reconstructed_path, mimetype='audio/mpeg')
        
        # Fallback: try constructed path
        artist_name = song.artist if song.artist else 'Unknown'
        if song.artist_id:
            artist_obj = Artist.query.get(song.artist_id)
            if artist_obj:
                artist_name = artist_obj.artist_name
        
        constructed_filename = f"{artist_name} - {song.name}.mp3"
        for directory in possible_dirs:
            if not directory:
                continue
            file_path = os.path.join(directory, constructed_filename) if os.path.isabs(directory) or os.path.sep in directory else os.path.join(app_root, directory, constructed_filename)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return send_file(file_path, mimetype='audio/mpeg')
        
        # If still not found, try searching for similar filenames (case-insensitive)
        song_name_lower = song.name.lower() if song.name else ''
        artist_name_lower = artist_name.lower() if artist_name != 'Unknown' else ''
        
        for directory in possible_dirs:
            if not directory or not os.path.exists(directory):
                continue
            try:
                for file in os.listdir(directory):
                    file_lower = file.lower()
                    # Check if filename contains song name or artist name (case-insensitive)
                    if file.endswith('.mp3') and (
                        (song_name_lower and song_name_lower in file_lower) or 
                        (artist_name_lower and artist_name_lower in file_lower)
                    ):
                        file_path = os.path.join(directory, file)
                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            return send_file(file_path, mimetype='audio/mpeg')
            except (OSError, PermissionError) as e:
                # Skip directories we can't read
                continue
        
        # Last resort: Try using Flask's static file serving mechanism
        # Construct relative path from static folder
        static_relative_paths = [
            f"afro/{constructed_filename}",
            f"afro/{filename}" if 'filename' in locals() else None,
            f"song_uploads/{constructed_filename}",
            f"song_uploads/{filename}" if 'filename' in locals() else None,
        ]
        
        for static_path in static_relative_paths:
            if not static_path:
                continue
            try:
                # Try with glconnect/static prefix
                glconnect_static = os.path.join(app_root, 'glconnect', 'static')
                if os.path.exists(glconnect_static):
                    full_path = os.path.join(glconnect_static, static_path)
                    if os.path.exists(full_path) and os.path.isfile(full_path):
                        # Extract the directory and filename for send_from_directory
                        static_dir = os.path.dirname(full_path)
                        static_filename = os.path.basename(full_path)
                        return send_from_directory(static_dir, static_filename, mimetype='audio/mpeg')
            except Exception:
                continue
        
        # Last resort: return a more detailed error message
        error_info = {
            "song_id": song_id,
            "song_name": song.name,
            "artist": artist_name,
            "local_path": song.local_path,
            "constructed_filename": constructed_filename,
            "app_root": app_root,
            "cwd": os.getcwd()
        }
        return jsonify({"error": "Song file not found", "details": error_info}), 404
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
