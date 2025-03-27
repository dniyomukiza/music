
from flask import render_template, Blueprint,request,session,jsonify
from .models import*

art = Blueprint("art", __name__)

@art.route('/artist/<int:artist_id>')
def artist_profile(artist_id):
    artist = Artist.query.get_or_404(artist_id)
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