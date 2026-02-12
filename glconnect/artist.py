
from flask import render_template, Blueprint,request,session,jsonify
from flask_login import current_user
from .models import*
import urllib.parse
from flask_cors import CORS


art = Blueprint("art", __name__)
def get_song_path(song, artist_name=None):
    """Helper function to get the correct path for a song"""
    import os
    
    # Check if it's a Song model or Song_upload model
    local_path = getattr(song, 'local_path', None)
    song_name = getattr(song, 'name', None) or getattr(song, 'name_song', None)
    song_artist = getattr(song, 'artist', None) or getattr(song, 'name_artist', None) or artist_name
    
    if local_path:
        # Extract filename from local_path if it's a full path
        if '/' in local_path or '\\' in local_path:
            filename = os.path.basename(local_path)
            if '/' in filename:
                filename = filename.split('/')[-1]
            if '\\' in filename:
                filename = filename.split('\\')[-1]
            return f"/static/afro/{filename}"
        else:
            # It's already a relative path or filename
            if local_path.startswith('/'):
                return local_path
            elif local_path.startswith('static/'):
                return f"/{local_path}"
            else:
                return f"/static/afro/{local_path}"
    else:
        # Fallback to constructed path
        if song_artist and song_name:
            return f"/static/afro/{urllib.parse.quote(song_artist)} - {urllib.parse.quote(song_name)}.mp3"
        return None

@art.route('/artist/<int:artist_id>')
def artist_profile(artist_id):
    artist = Artist.query.get_or_404(artist_id)

    # Get songs uploaded by the artist via Song model (only approved for public view)
    from sqlalchemy import or_
    songs_from_song_model = Song.query.filter_by(artist_id=artist_id).filter(
        or_(Song.approval_status.is_(None), Song.approval_status == 'approved')
    ).all()

    # Get songs uploaded via Song_upload model (only approved)
    songs_from_upload_model = Song_upload.query.filter_by(name_artist=artist.artist_name).filter(
        or_(Song_upload.approval_status.is_(None), Song_upload.approval_status == 'approved')
    ).all()

    # Add path attribute to each song object
    for song in songs_from_song_model:
        song.song_path = get_song_path(song, artist.artist_name)
    
    for song_upload in songs_from_upload_model:
        song_upload.song_path = get_song_path(song_upload, artist.artist_name)

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
    from flask import url_for
    playlist_entries = Playlist.query.filter_by(user_id=user_id).all()
    songs = []
    for entry in playlist_entries:
        if entry.song_id:
            song = Song.query.get(entry.song_id)
            if not song:
                continue
            # Get the artist details using the artist_id from the song
            artist = Artist.query.get(song.artist_id)
            if artist:
                artist_name = artist.artist_name
            else:
                artist_name = "Unknown Artist"

            # Use local_path if available, otherwise construct path
            if song.local_path:
                # Extract filename from local_path if it's a full path
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
                song_path = f"/static/afro/{urllib.parse.quote(song.artist)} - {urllib.parse.quote(song.name)}.mp3"
            
            songs.append({
                'song_id': song.id,
                'song_name': song.name,
                'artist_name': artist_name,
                'song_url': song_path
            })
        elif entry.download_id:
            d = DownloadedSong.query.get(entry.download_id)
            if d:
                songs.append({
                    'song_id': None,
                    'song_name': d.name or 'Untitled',
                    'artist_name': d.artist or 'Unknown',
                    'song_url': url_for('playlist2.serve_downloaded_song_file', download_id=d.id)
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
