import re
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os,subprocess
from glconnect import db
from urllib.parse import urlparse
from glconnect.models import *

music = Blueprint("music", __name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "glconnect", "static", "song_uploads")
ALLOWED_EXTENSIONS = {'mp3', 'ogg'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit for file uploads

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_input(input_string):
    """Sanitize user inputs to prevent SQL injection and other attacks"""
    if input_string:
        # Strip leading/trailing spaces
        sanitized_string = input_string.strip()

        # Remove any non-alphanumeric characters except for space, hyphen, or period
        sanitized_string = re.sub(r'[^a-zA-Z0-9\s\-\.\/\:]','', sanitized_string)

        return sanitized_string
    return ""

def sanitize_url(url):
    """Sanitize and enforce HTTPS for URLs."""
    if url:
        sanitized_url = sanitize_input(url)

        # Enforce https:// by default
        if not sanitized_url.startswith('http://') and not sanitized_url.startswith('https://'):
            sanitized_url = 'https://' + sanitized_url

        # Validate URL structure
        parsed = urlparse(sanitized_url)
        if parsed.scheme in ['http', 'https'] and parsed.netloc:
            return sanitized_url
    return ""
@music.route("/upload_song", methods=["GET", "POST"])
@login_required
def upload_song():
    if request.method == "GET":
        return render_template("upload_song.html")

    song_name = sanitize_input(request.form.get("song_name"))
    artist_name = sanitize_input(request.form.get("artist_name")) or current_user.username

    song_file = request.files.get("song_file")
    cover_image_file = request.files.get("cover_image")

    # Social media links sanitization
    twitter_link = sanitize_url(request.form.get("twitter"))
    instagram_link = sanitize_url(request.form.get("instagram"))
    spotify_link = sanitize_url(request.form.get("spotify"))
    apple_music_link = sanitize_url(request.form.get("apple_music"))

    # Validation
    if not song_file or song_file.filename == "":
        flash("No song file uploaded.", "error")
        return redirect(url_for("music.upload_song"))

    if not song_file.filename.lower().endswith('.mp3'):
        flash("Only MP3 files are allowed.", "error")
        return redirect(url_for("music.upload_song"))

    if song_file.content_length > MAX_FILE_SIZE:
        flash("File is too large. Maximum allowed size is 50 MB.", "error")
        return redirect(url_for("music.upload_song"))

    artist = Artist.query.filter_by(artist_name=artist_name).first()
    if not artist:
        flash(f"Artist {artist_name} not found.", "error")
        return redirect(url_for("music.upload_song"))

    # Create filename with spaces and dashes (not underscores)
    # Sanitize but preserve spaces and dashes
    def sanitize_filename_preserve_spaces(text):
        """Sanitize filename but preserve spaces and dashes"""
        import re
        # Keep alphanumeric, spaces, dashes, and dots
        sanitized = re.sub(r'[^a-zA-Z0-9\s\-\.]', '', text)
        # Remove multiple consecutive spaces
        sanitized = re.sub(r'\s+', ' ', sanitized)
        # Strip leading/trailing spaces and dashes
        sanitized = sanitized.strip(' -')
        return sanitized
    
    # Format: "Artist Name - Song Name.mp3" with spaces preserved
    base_filename = f"{sanitize_filename_preserve_spaces(artist_name)} - {sanitize_filename_preserve_spaces(song_name)}"
    mp3_filename = f"{base_filename}.mp3"
    mp3_path = os.path.join(UPLOAD_FOLDER, mp3_filename)
    
    counter = 1
    while os.path.exists(mp3_path):
        mp3_filename = f"{base_filename} ({counter}).mp3"
        mp3_path = os.path.join(UPLOAD_FOLDER, mp3_filename)
        counter += 1

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    song_file.save(mp3_path)

    # Handle cover image
    if cover_image_file and cover_image_file.filename != "":
        cover_filename = secure_filename(cover_image_file.filename)
        cover_path = os.path.join(UPLOAD_FOLDER, cover_filename)
        cover_image_file.save(cover_path)
    else:
        cover_filename = "cover.webp"

    new_song = Song_upload(
        name_song=song_name,
        name_artist=artist_name,
        local_path=os.path.join("/static/song_uploads", mp3_filename),
        cover_image=cover_filename,
        twitter_link=twitter_link,
        instagram_link=instagram_link,
        spotify_link=spotify_link,
        apple_music_link=apple_music_link,
        artist_id=artist.artist_id
    )

    try:
        db.session.add(new_song)
        db.session.commit()
        flash("MP3 song uploaded successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Database error occurred.", "error")

    return redirect(url_for("art.artist_profile", artist_id=artist.artist_id))



def get_song_path_for_artist(song, artist_name=None):
    """Helper function to get the correct path for a song in artist profile"""
    import os
    import urllib.parse
    
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
            # Check if file exists in song_uploads directory
            song_uploads_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(song_uploads_path):
                return f"/static/song_uploads/{filename}"
            # Fallback to afro directory
            return f"/static/afro/{filename}"
        else:
            # It's already a relative path or filename
            if local_path.startswith('/'):
                return local_path
            elif local_path.startswith('static/'):
                return f"/{local_path}"
            else:
                # Check if file exists in song_uploads directory
                song_uploads_path = os.path.join(UPLOAD_FOLDER, local_path)
                if os.path.exists(song_uploads_path):
                    return f"/static/song_uploads/{local_path}"
                # Fallback to afro directory
                return f"/static/afro/{local_path}"
    else:
        # Fallback to constructed path - try song_uploads first
        if song_artist and song_name:
            constructed_filename = f"{song_artist} - {song_name}.mp3"
            song_uploads_path = os.path.join(UPLOAD_FOLDER, constructed_filename)
            if os.path.exists(song_uploads_path):
                return f"/static/song_uploads/{urllib.parse.quote(constructed_filename)}"
            # Fallback to afro directory
            return f"/static/afro/{urllib.parse.quote(song_artist)} - {urllib.parse.quote(song_name)}.mp3"
        return None

@music.route("/artist_profile")
@login_required
def artist_profile():
    artist = current_user.artist_profile

    if not artist:
        return redirect(url_for("routes.index"))

    # Get songs uploaded by the artist (via artist_id) from Song model
    uploaded_songs = Song.query.filter_by(artist_id=artist.artist_id).all()

    # Get songs uploaded via Song_upload model (assuming artist_name is stored in Song_upload)
    uploaded_songs_upload = Song_upload.query.filter_by(name_artist=artist.artist_name).all()

    # Add path attribute to each song object
    for song in uploaded_songs:
        song.song_path = get_song_path_for_artist(song, artist.artist_name)
    
    for song_upload in uploaded_songs_upload:
        song_upload.song_path = get_song_path_for_artist(song_upload, artist.artist_name)

    # Combine both song lists (no duplicates based on song ID)
    all_songs = uploaded_songs + uploaded_songs_upload

    return render_template("artists.html", user=current_user, artist=artist, songs=all_songs)



@music.route("/delete_song/<int:song_id>", methods=["POST"])
@login_required
def delete_song(song_id):
    # Try to find the song in Song table first
    song = Song.query.get(song_id)

    # If not found, try Song_upload table
    if not song:
        song = Song_upload.query.get(song_id)

    if not song:
        flash("Song not found.")
        return redirect(url_for("music.artist_profile"))

    # Check artist ownership
    artist_id = getattr(song, 'artist_id', None)
    current_artist_id = getattr(current_user.artist_profile, 'artist_id', None)
    print("Song artist_id:", getattr(song, 'artist_id', None))
    print("Current user artist_id:", getattr(current_user.artist_profile, 'artist_id', None))

    if artist_id != current_artist_id:
        flash("You do not have permission to delete this song.")
        return redirect(url_for("music.artist_profile", artist_id=current_artist_id))

    # Delete from database
    db.session.delete(song)
    db.session.commit()

    flash("Song deleted successfully!")
    return redirect(url_for("music.artist_profile", artist_id=current_artist_id))


@music.route('/delete-profile', methods=['POST'])
@login_required
def delete_profile():
    artist = Artist.query.filter_by(user_id=current_user.user_id).first()

    if not artist:
        flash("Profile not found.", "warning")
        return redirect(url_for('routes.index'))

    # Remove associated songs from the database
    songs = Song.query.filter_by(artist_id=artist.artist_id).all()
    for song in songs:
        db.session.delete(song)

    # Delete the artist profile
    db.session.delete(artist)

    try:
        db.session.commit()
        flash("Your profile and all associated data have been deleted.", "success")
        return redirect(url_for('routes.index'))  # Redirect to home or another page
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('routes.index'))
    
@music.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.username = request.form['username']
        current_user.bio = request.form.get('bio')

        profile_picture = request.files.get('profile_picture')
        if profile_picture and profile_picture.filename != '':
            filename = secure_filename(profile_picture.filename)
            picture_path = os.path.join('static/profile_pics', filename)
            profile_picture.save(picture_path)
            current_user.profile_picture = filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('music.edit_profile'))

    return render_template('user_edit.html')


@music.route('/edit_artist', methods=['GET', 'POST'])
@login_required
def artist_edit():
    artist = current_user.artist_profile

    if not artist:
        flash('No artist profile found for this user.', 'error')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        artist_name = request.form.get('artist_name')
        bio = request.form.get('bio')

        # Update artist name and bio only if they were modified
        if artist.artist_name != artist_name:
            artist.artist_name = artist_name
        if artist.bio != bio:
            artist.bio = bio

        # Handling profile picture update
        profile_pic = request.files.get('profile_pic')
        if profile_pic and profile_pic.filename != '':
            filename = secure_filename(profile_pic.filename)

            # Define the folder where the profile picture will be stored
            upload_folder = os.path.join(os.getcwd(), 'glconnect', 'static', 'uploads')

            # Ensure the directory exists before saving
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # Set the file path where the profile picture will be saved
            filepath = os.path.join(upload_folder, filename)
            profile_pic.save(filepath)

            # Save the path as static/uploads/picname.jpg in database
            artist.profile_pic = f"static/uploads/{filename}"

        # Commit changes to the database
        db.session.commit()

        # Flash success message
        flash('Artist profile updated successfully!', 'success')
        return redirect(url_for('music.artist_profile'))

    return render_template('artist_edit.html', artist=artist)



