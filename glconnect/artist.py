
from flask import render_template, Blueprint,request,session,jsonify
from flask_login import current_user
from .models import*
import urllib.parse


art = Blueprint("art", __name__)

@art.route('/artist/<int:artist_id>')
def artist_profile(artist_id):
    artist = Artist.query.get_or_404(artist_id)

    # Get songs uploaded by the artist via Song model
    songs_from_song_model = Song.query.filter_by(artist_id=artist_id).all()

    # Get songs uploaded via Song_upload model (where name_artist matches the artist_name)
    songs_from_upload_model = Song_upload.query.filter_by(name_artist=artist.artist_name).all()

    # Combine both song lists (no duplicates based on song ID)
    all_songs = songs_from_song_model + songs_from_upload_model

    return render_template('artist_profile.html', artist=artist, songs=all_songs)

@art.route('/add_to_playlist', methods=['POST'])
def add_to_playlist():
    song_id = request.json.get('song_id')
    user_id = session.get('user_id')

    # Check if the song is already in the user's playlist
    existing_entry = Playlist.query.filter_by(user_id=user_id, song_id=song_id).first()
    if existing_entry:
        return jsonify({'message': 'Song already in playlist'}), 400

    # Add the new song to the playlist
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

    return jsonify({'message': 'Playlist saved successfully. Refresh page'}), 200


@art.route('/get_playlist/<int:user_id>', methods=['GET'])
def get_playlist(user_id):
    # Retrieve the user's playlist entries
    playlist_entries = Playlist.query.filter_by(user_id=user_id).all()

    # Get the song details for each playlist entry
    songs = []
    for entry in playlist_entries:
        song = Song.query.get(entry.song_id)
        if song:
            # Get the artist details using the artist_id from the song
            artist = Artist.query.get(song.artist_id)
            if artist:
                artist_name = artist.artist_name
            else:
                artist_name = "Unknown Artist"

            # Construct the song path using the artist and song name
            song_path = f"/static/afro/{urllib.parse.quote(song.artist)} - {urllib.parse.quote(song.name)}.mp3"
            
            songs.append({
                'song_id': song.id,
                'song_name': song.name,
                'artist_name': artist_name,  # Add artist name to the response
                'song_url': song_path  # Return the dynamically constructed song path
            })

    if not songs:
        return jsonify({'message': 'No songs found in playlist'}), 404

    return jsonify({'playlist': songs}), 200

from flask import request, jsonify
from flask_login import current_user, login_required
import traceback
from .models import Playlist, db  # Adjust import based on your structure

@art.route('/delete_song_from_playlist', methods=['DELETE'])
@login_required
def delete_song_from_playlist():
    try:
        data = request.get_json()
        print(f"Request data: {data}")

        song_id = data.get('song_id')
        if not song_id:
            print("Missing song_id!")
            return jsonify({'message': 'song_id is required'}), 400

        # Ensure current_user has user_id
        user_id = getattr(current_user, 'user_id', None)
        if not user_id:
            print("User not authenticated or missing user_id")
            return jsonify({'message': 'User not authenticated'}), 401

        # Attempt to find and delete the song
        song = Playlist.query.filter_by(song_id=song_id, user_id=user_id).first()
        if song:
            print(f"Deleting song: {song}")
            db.session.delete(song)
            db.session.commit()
            return jsonify({'message': 'Song removed from playlist!'}), 200
        else:
            print(f"Song with ID {song_id} not found for user_id {user_id}")
            return jsonify({'message': 'Song not found in playlist'}), 404

    except Exception as e:
        print("Exception occurred while deleting song:")
        traceback.print_exc()
        return jsonify({'message': 'Internal server error'}), 500
