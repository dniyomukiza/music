import re
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os,subprocess
from glconnect import db
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
    """Sanitize URL to ensure it starts with http:// or https://"""
    if url:
        # Remove any unwanted characters
        sanitized_url = sanitize_input(url)

        # Ensure URL starts with http:// or https://
        if not sanitized_url.startswith('http://') and not sanitized_url.startswith('https://'):
            sanitized_url = 'http://' + sanitized_url
        
        # Check if the URL has a valid format
        url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
        if re.match(url_pattern, sanitized_url):
            return sanitized_url
        else:
            return ""  # Invalid URL, return empty string
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

    if not allowed_file(song_file.filename):
        flash("Only MP3 or OGG files are allowed.", "error")
        return redirect(url_for("music.upload_song"))

    if song_file.content_length > MAX_FILE_SIZE:
        flash("File is too large. Maximum allowed size is 50 MB.", "error")
        return redirect(url_for("music.upload_song"))

    # Secure file naming
    base_filename = secure_filename(f"{artist_name} - {song_name}")
    mp3_filename = f"{base_filename}.mp3"
    ogg_filename = f"{base_filename}.ogg"

    mp3_path = os.path.join(UPLOAD_FOLDER, mp3_filename)
    ogg_path = os.path.join(UPLOAD_FOLDER, ogg_filename)

    # Ensure unique filenames
    counter = 1
    while os.path.exists(mp3_path) or os.path.exists(ogg_path):
        mp3_filename = f"{base_filename} ({counter}).mp3"
        ogg_filename = f"{base_filename} ({counter}).ogg"
        mp3_path = os.path.join(UPLOAD_FOLDER, mp3_filename)
        ogg_path = os.path.join(UPLOAD_FOLDER, ogg_filename)
        counter += 1

    # Ensure the upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Save the song file (skip conversion if it's an .ogg file)
    if song_file.filename.endswith('.ogg'):
        song_file.save(ogg_path)
        final_filename = ogg_filename
    else:
        song_file.save(mp3_path)
        # Convert MP3 to OGG
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", mp3_path, "-c:a", "libvorbis", ogg_path
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Converted to OGG: {ogg_path}")
            final_filename = ogg_filename
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr.decode()}")
            flash("Error converting file to OGG.", "error")
            return redirect(url_for("music.upload_song"))

    # Handle cover image
    if cover_image_file and cover_image_file.filename != "":
        cover_filename = secure_filename(cover_image_file.filename)
        cover_path = os.path.join(UPLOAD_FOLDER, cover_filename)
        cover_image_file.save(cover_path)
    else:
        cover_filename = "cover.webp"  # fallback default

    # Save to database
    new_song = Song_upload(
        name_song=song_name,
        name_artist=artist_name,
        local_path=os.path.join("/static/song_uploads", final_filename),
        cover_image=cover_filename,
        twitter_link=twitter_link,
        instagram_link=instagram_link,
        spotify_link=spotify_link,
        apple_music_link=apple_music_link
    )

    try:
        db.session.add(new_song)
        db.session.commit()
        flash("Song uploaded and converted successfully!" if song_file.filename.endswith('.mp3') else "Song uploaded successfully!", "success")
    except Exception as e:
        print(f"Database error: {e}")
        flash("Database error occurred.", "error")

    return redirect(url_for("music.upload_song"))


    return redirect(url_for("music.upload_song"))
@music.route("/artist_profile")
@login_required
def artist_profile():
    return render_template("artists.html", user=current_user)
