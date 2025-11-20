from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from glconnect.models import Song, Playlist, db,Artist

play = Blueprint('playlist2', __name__)

from flask import url_for

# In your route for fetching songs
@play.route('/playlist2', methods=['GET'])
def playlist2():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])

    # 1. Exact match for artist (case-insensitive) - redirect to profile
    artist = Artist.query.filter(db.func.lower(Artist.artist_name) == query).first()
    if artist:
        return jsonify({
            'redirect': url_for('art.artist_profile', artist_id=artist.artist_id)
        })

    # 2. Search for songs matching the query (partial match for song name)
    songs = Song.query.filter(db.func.lower(Song.name).like(f'%{query}%')).limit(20).all()
    
    if songs:
        # Return array of songs
        songs_data = []
        for song in songs:
            # Get artist name - prefer artist field, fallback to artist_id lookup
            artist_name = song.artist if song.artist else 'Unknown'
            if not artist_name or artist_name == 'Unknown':
                if song.artist_id:
                    artist = Artist.query.get(song.artist_id)
                    if artist:
                        artist_name = artist.artist_name
            
            songs_data.append({
                'id': song.id,
                'name': song.name,
                'artist': artist_name
            })
        return jsonify(songs_data)
    
    # 3. Partial match for artist name (if no songs found)
    artist_partial = Artist.query.filter(db.func.lower(Artist.artist_name).like(f'%{query}%')).first()
    if artist_partial:
        return jsonify({
            'redirect': url_for('art.artist_profile', artist_id=artist_partial.artist_id)
        })

    # 4. Exact match for song name (if no partial matches)
    song = Song.query.filter(db.func.lower(Song.name) == query).first()
    if song:
        return jsonify({
            'redirect': url_for('art.artist_profile', artist_id=song.artist_id)
        })

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
            
            songs_data.append({
                'id': song.id,
                'name': song.name,
                'artist': artist_name
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
            playlist_data.append({
                'id': song.id,
                'name': song.name,
                'artist': song.artist,
                'local_path': song.local_path,
                'spotify_id': song.spotify_id,
                'is_available_on_spotify': song.is_available_on_spotify
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
