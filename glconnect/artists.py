from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from glconnect import db
from glconnect.models import Song

music = Blueprint("music", __name__)

UPLOAD_FOLDER = "static/audio"
ALLOWED_EXTENSIONS = {"mp3",".ogg",".wav"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True) 

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@music.route("/upload_song", methods=["GET", "POST"])
@login_required
def upload_song():
    if request.method == "GET":
        return render_template("upload_song.html") 

    # Handle song upload
    if "song_file" not in request.files:
        flash("No file uploaded.", "error")
        print("No file uploaded.")
        return redirect(url_for("music.upload_song"))

    file = request.files["song_file"]
    song_name = request.form.get("song_name")

    if file.filename == "" or not allowed_file(file.filename):
        flash("Invalid file format. Only MP3 files are allowed.", "error")
        print(f"Invalid file format: {file.filename}")
        return redirect(url_for("music.upload_song"))

    artist_name = current_user.username  
    filename = secure_filename(f"{artist_name} - {song_name}.mp3")
    filename = secure_filename(filename).replace("_", " ") 
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    print(f"Attempting to save file: {filename}")
    # Ensure unique filename
    counter = 1
    base_filename, extension = os.path.splitext(filename)
    while os.path.exists(file_path):
        filename = f"{base_filename} ({counter}){extension}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        counter += 1

    print(f"Saving to path: {file_path}")  # Debug print
    file.save(file_path)

    # Save song metadata in the database
    new_song = Song(
        name=song_name,
        artist=artist_name,
        local_path=file_path,
        spotify_id=None,
        is_available_on_spotify=False
    )
    try:
        db.session.add(new_song)
        db.session.commit()
        print(f"Song added to database: {song_name} by {artist_name}")
    except Exception as e:
        print(f"Error saving song to database: {e}")
        flash("An error occurred while saving the song.", "error")
        return redirect(url_for("music.upload_song"))

    flash("Song uploaded successfully!", "success")
    print(f"Song uploaded successfully: {song_name} by {artist_name}") 
    return redirect(url_for("music.upload_song"))


@music.route("/artist_profile")
@login_required
def artist_profile():
    return render_template("artists.html", user=current_user)
