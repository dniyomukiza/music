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

    # Search for the artist by name
    artist = Artist.query.filter(db.func.lower(Artist.artist_name) == query).first()
    if artist:
        # Return the artist ID along with other data
        return jsonify({
            'redirect': url_for('art.artist_profile', artist_id=artist.artist_id)  # Use artist_id here
        })

    # If no artist is found, search for songs
    song = Song.query.filter(db.func.lower(Song.name) == query).first()
    if song:
        # Redirect to the artist's profile associated with the song
        return jsonify({
            'redirect': url_for('art.artist_profile', artist_id=song.artist_id)  # Redirect to artist's profile
        })

    return jsonify([])  # If no song or artist is found




@play.route('/add_to_playlist', methods=['POST'])
@login_required
def add_to_playlist():
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
