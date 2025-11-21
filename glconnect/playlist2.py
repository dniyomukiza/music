from flask import Blueprint, request, jsonify, send_from_directory, send_file
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
    for song in songs_from_song_model:
        artist_name_display = song.artist if song.artist else 'Unknown'
        if not artist_name_display or artist_name_display == 'Unknown':
            if song.artist_id:
                artist_obj = Artist.query.get(song.artist_id)
                if artist_obj:
                    artist_name_display = artist_obj.artist_name
        
        # Use local_path if available, otherwise construct path (same logic as template routes)
        if song.local_path:
            # Extract filename from local_path if it's a full path
            if '/' in song.local_path or '\\' in song.local_path:
                # It's a full path, extract just the filename
                filename = os.path.basename(song.local_path)
                # Remove any directory prefixes like 'ytauto/', 'afro/', etc.
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
            song_name_for_path = song.name if song.name else 'Untitled Track'
            song_path = f"/static/afro/{urllib.parse.quote(artist_name_display)} - {urllib.parse.quote(song_name_for_path)}.mp3"
        
        # Ensure name is not empty or None
        song_name = song.name.strip() if song.name and song.name.strip() else 'Untitled Track'
        
        songs_data.append({
            'id': song.id,
            'name': song_name,
            'artist': artist_name_display,
            'path': song_path  # Include the path in the response (matches template route logic)
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
        songs_data = []
        for song in songs:
            artist_name = song.artist if song.artist else 'Unknown'
            if not artist_name or artist_name == 'Unknown':
                if song.artist_id:
                    artist = Artist.query.get(song.artist_id)
                    if artist:
                        artist_name = artist.artist_name
            
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
                song_name_for_path = song.name if song.name else 'Untitled Track'
                song_path = f"/static/afro/{urllib.parse.quote(artist_name)} - {urllib.parse.quote(song_name_for_path)}.mp3"
            
            # Ensure name is not empty or None
            song_name = song.name.strip() if song.name and song.name.strip() else 'Untitled Track'
            
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
                song_name_for_path = song.name if song.name else 'Untitled Track'
                song_path = f"/static/afro/{urllib.parse.quote(artist_name)} - {urllib.parse.quote(song_name_for_path)}.mp3"
            
            # Ensure name is not empty or None
            song_name = song.name.strip() if song.name and song.name.strip() else 'Untitled Track'
            
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
            
            # Use local_path if available, otherwise construct path
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
                    song_path = song.local_path if song.local_path.startswith('/') else f"/static/afro/{song.local_path}"
            else:
                # Fallback to constructed path
                import urllib.parse
                song_path = f"/static/afro/{urllib.parse.quote(artist_name)} - {urllib.parse.quote(song.name)}.mp3"
            
            # Ensure name is not empty or None
            song_name = song.name.strip() if song.name and song.name.strip() else 'Untitled Track'
            
            playlist_data.append({
                'id': song.id,
                'name': song_name,
                'artist': artist_name,
                'path': song_path  # Include the path in the response
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
        song = Song.query.get_or_404(song_id)
        
        # Try to find the file using local_path if available
        if song.local_path:
            # If local_path is a full path, extract filename
            if '/' in song.local_path or '\\' in song.local_path:
                filename = os.path.basename(song.local_path)
            else:
                filename = song.local_path
            
            # Try multiple possible locations
            possible_dirs = [
                'glconnect/static/afro',
                'static/afro',
                '/usr/src/appdir/glconnect/static/afro',
                os.path.join(os.getcwd(), 'glconnect', 'static', 'afro'),
            ]
            
            for directory in possible_dirs:
                file_path = os.path.join(directory, filename)
                if os.path.exists(file_path):
                    return send_file(file_path, mimetype='audio/mpeg')
        
        # Fallback: try constructed path
        artist_name = song.artist if song.artist else 'Unknown'
        if song.artist_id:
            artist_obj = Artist.query.get(song.artist_id)
            if artist_obj:
                artist_name = artist_obj.artist_name
        
        constructed_filename = f"{artist_name} - {song.name}.mp3"
        for directory in possible_dirs:
            file_path = os.path.join(directory, constructed_filename)
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='audio/mpeg')
        
        # If still not found, try searching for similar filenames
        for directory in possible_dirs:
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    # Check if filename contains song name or artist name
                    if (song.name.lower() in file.lower() or 
                        (artist_name != 'Unknown' and artist_name.lower() in file.lower())):
                        file_path = os.path.join(directory, file)
                        if os.path.exists(file_path) and file.endswith('.mp3'):
                            return send_file(file_path, mimetype='audio/mpeg')
        
        return jsonify({"error": "Song file not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
