
from flask import render_template, Blueprint,request,session,jsonify
from .models import*
import urllib.parse


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
    user_id = session.get('user_id')  

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

@art.route('/save_playlist', methods=['POST'])
def save_playlist():
    data = request.get_json()
    user_id = session.get('user_id')
    song_ids = data.get('song_ids')

    # Ensure user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found be sure you are logged in'}), 400

    # Ensure that songs exist in the database
    for song_id in song_ids:
        song = Song.query.get(song_id)
        if not song:
            return jsonify({'message': f'Song with ID {song_id} not found'}), 400
        # Log the data being added to the session
        print(f"Adding song ID {song_id} to playlist for user ID {user_id}")
        new_playlist_entry = Playlist(user_id=user_id, song_id=song_id)
        db.session.add(new_playlist_entry)

    # Log before committing the changes
    print(f"Committing changes to the database...")
    db.session.commit()

    return jsonify({'message': 'Playlist saved successfully'}), 200


@art.route('/get_playlist/<int:user_id>', methods=['GET'])
def get_playlist(user_id):
    # Retrieve the user's playlist
    playlist_entries = Playlist.query.filter_by(user_id=user_id).all()

    # Get the song details for each playlist entry
    songs = []
    for entry in playlist_entries:
        song = Song.query.get(entry.song_id)
        if song:
            # Construct the song path using the artist and song name
            song_path = f"/static/afro/{urllib.parse.quote(song.artist)} - {urllib.parse.quote(song.name)}.ogg"
            
            songs.append({
                'song_id': song.id,
                'song_name': song.name,
                'song_url': song_path  # Return the dynamically constructed song path
            })

    if not songs:
        return jsonify({'message': 'No songs found in playlist'}), 404

    return jsonify({'playlist': songs}), 200
