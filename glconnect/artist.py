
from flask import render_template, Blueprint,request,session,jsonify
from .models import*

art = Blueprint("art", __name__)

@art.route('/artist/<int:artist_id>')
def artist_profile(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    if artist is None:
        print(f"Artist with ID {artist_id} not found.") 
    songs = Song.query.filter_by(artist_id=artist_id).all()
    return render_template('artist_profile.html', artist=artist, songs=songs)
@art.route('/add_to_playlist', methods=['POST'])
def add_to_playlist():
    song_id = request.json.get('song_id')
    user_id = session.get('user_id')  # Assuming user_id is stored in session

    # Check if the song is already in the user's playlist
    existing_entry = Playlist.query.filter_by(user_id=user_id, song_id=song_id).first()
    if existing_entry:
        return jsonify({'message': 'Song already in playlist'}), 400

    # Add song to playlist
    new_playlist_entry = Playlist(user_id=user_id, song_id=song_id)
    db.session.add(new_playlist_entry)
    db.session.commit()

    return jsonify({'message': 'Song added to playlist'}), 200

@art.route('/remove_from_playlist', methods=['POST'])
def remove_from_playlist():
    song_id = request.json.get('song_id')
    user_id = session.get('user_id')

    # Remove song from playlist
    playlist_entry = Playlist.query.filter_by(user_id=user_id, song_id=song_id).first()
    if not playlist_entry:
        return jsonify({'message': 'Song not found in playlist'}), 404

    db.session.delete(playlist_entry)
    db.session.commit()

    return jsonify({'message': 'Song removed from playlist'}), 200

@art.route('/get_playlist', methods=['GET'])
def get_playlist():
    user_id = session.get('user_id')
    playlist = Playlist.query.filter_by(user_id=user_id).all()
    songs = [{'song_id': entry.song_id, 'added_on': entry.added_on} for entry in playlist]

    return jsonify(songs), 200





@art.route('/save_playlist', methods=['POST'])
def save_playlist():
    data = request.get_json()
    user_id = data.get('user_id')
    song_ids = data.get('song_ids')  # List of song IDs
    
    # Ensure user exists (Optional check)
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Add each song to the playlist
    try:
        for song_id in song_ids:
            song = Song.query.get(song_id)
            if not song:
                continue  # Skip if the song is not found
            # Create new playlist entry
            new_playlist_entry = Playlist(user_id=user_id, song_id=song_id)
            db.session.add(new_playlist_entry)
        db.session.commit()
        return jsonify({'message': 'Playlist saved successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error saving playlist: {str(e)}'}), 500

# Route to load the playlist
@art.route('/load_playlist', methods=['GET'])
def load_playlist():
    user_id = request.args.get('user_id')  # Retrieve user_id from query params
    
    # Get the playlist for the user
    playlist_entries = Playlist.query.filter_by(user_id=user_id).all()
    
    if not playlist_entries:
        return jsonify({'message': 'No playlist found for this user'}), 404
    
    # Get song details for the playlist
    playlist_data = []
    for entry in playlist_entries:
        song = Song.query.get(entry.song_id)
        playlist_data.append({
            'song_id': song.id,
            'song_name': song.name,
            'artist': song.artist,
            'added_on': entry.added_on
        })
    
    return jsonify({'playlist': playlist_data}), 200