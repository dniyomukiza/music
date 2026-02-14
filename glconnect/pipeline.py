import os
import json
from flask import Flask
from subprocess import run
from dotenv import load_dotenv
try:
    from glconnect.models import db, Song, DownloadedSong
except ImportError:
    from models import db, Song, DownloadedSong

# Load configuration from environment variables
config = {
    "DB_URL": os.getenv("DB_URL", "postgresql://music_owqr_user:D8SRPZ7ubYN79Pdh6E8aKzg4O2yirBrL@dpg-ct1ae39u0jms73cdpjdg-a.oregon-postgres.render.com/music_owqr")
}
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DB_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "abarayon"
db.init_app(app)

# Connect to existing database (don't create tables)
# with app.app_context():
#     db.create_all()

# Path to your output folder for music files
output_folder = os.path.join(os.getcwd(), "glconnect/static/ytauto")

class AudioDownloader:
    def __init__(self, playlist_url=None, output_folder=None):
        self.playlist_url = playlist_url.strip() if playlist_url else None
        self.output_folder = os.path.expanduser(output_folder) if output_folder else os.getcwd()

    def prepare_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)

    def download_audio(self):
        if not self.playlist_url:
            raise ValueError("No playlist URL provided for downloading.")
        import shutil
        ytdlp_path = shutil.which("yt-dlp")
        if not ytdlp_path:
            raise FileNotFoundError(
                "yt-dlp is not installed or not in PATH. Install it (e.g. pip install yt-dlp or brew install yt-dlp) and try again."
            )
        self.prepare_output_folder()
        print(f"Downloading to folder: {self.output_folder}")
        command = [
            ytdlp_path,
            "-x", 
            "--audio-format", "mp3",  
            "--audio-quality", "0",
            "--yes-playlist", 
            "-o", os.path.join(self.output_folder, "%(title)s.%(ext)s"),
            self.playlist_url,
        ]
        print(f"Running command: {' '.join(command)}")
        result = run(command)
        if result.returncode == 0:
            print(f"Download completed successfully!")
            print(f"Files saved to: {self.output_folder}")
        else:
            print(f"An error occurred during the download process.")
            print(f"Return code: {result.returncode}")

    def download_and_convert(self):
        self.download_audio()

class MusicFileRenamer:
    @staticmethod
    def clean_music_names(directory):
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist yet. Skipping rename step.")
            return
        
        os.chdir(directory)
        for filename in os.listdir(directory):
            try:
                base_name, extension = os.path.splitext(filename)
                
                # Remove brackets and their content (e.g., [Official Video], [Audio])
                import re
                base_name = re.sub(r'\[.*?\]', '', base_name)
                
                # Remove parentheses and their content (e.g., (Official Video), (feat. Artist))
                base_name = re.sub(r'\(.*?\)', '', base_name)
                
                # Remove special characters but keep spaces and hyphens
                base_name = re.sub(r'[^\w\s\-&]', '', base_name)
                
                # Clean up multiple spaces and trim
                base_name = re.sub(r'\s+', ' ', base_name).strip()
                
                # Handle the artist - song format
                parts = base_name.split(" - ")
                if len(parts) == 2:
                    artist = parts[0].strip()
                    song = parts[1].strip()
                    new_filename = f"{artist} - {song}{extension}"
                    
                    # Only rename if the filename actually changed
                    if new_filename != filename:
                        os.rename(filename, new_filename)
                        print(f"Renamed: {filename} -> {new_filename}")
                    else:
                        print(f"No changes needed: {filename}")
                else:
                    print(f"Skipping file (unexpected format): {filename}")
            except Exception as e:
                print(f"Error renaming {filename}: {e}")

class PlaylistIngestion:
    @staticmethod
    def extract_name_artist(file_path):
        file_path = os.path.normpath(file_path)
        keyword = os.path.join("ytauto", "") 
        if keyword in file_path:
            relative_path = file_path.split(keyword, 1)[1]
        else:
            print(f"Skipping file, 'ytauto/' not found in path: {file_path}")
            return None, None  
        
        # Extract artist and song name
        if ' - ' in relative_path:
            artist, song_name = relative_path.split(' - ', 1)
            song_name = song_name.replace('.mp3', '').strip()
        else:
            artist = None
            song_name = os.path.basename(relative_path).replace('.mp3', '').strip()
    
        return artist, song_name

    @staticmethod
    def ingest_songs_from_m3u(file_path):
        """Ingest YouTube-downloaded tracks into downloaded_songs table only (not songs)."""
        with app.app_context():
            with open(file_path, 'r') as m3u_file:
                added_count = 0
                skipped_count = 0
                for line in m3u_file:
                    line = line.strip()
                    if line:
                        artist, song_name = PlaylistIngestion.extract_name_artist(line)
                        if artist is None and song_name is None:
                            continue
                        existing = DownloadedSong.query.filter_by(
                            artist=artist,
                            name=song_name
                        ).first()
                        if existing:
                            print(f"Skipped duplicate download: {artist} - {song_name}")
                            skipped_count += 1
                        else:
                            row = DownloadedSong(name=song_name, artist=artist, local_path=line)
                            db.session.add(row)
                            print(f"Added download: {artist} - {song_name}")
                            added_count += 1
                db.session.commit()
                print(f"Download ingestion complete: {added_count} added, {skipped_count} skipped.")

    @staticmethod
    def save_song_to_db(artist, song_name, local_path):
        """Save one YouTube-downloaded track to downloaded_songs table."""
        with app.app_context():
            existing = DownloadedSong.query.filter_by(artist=artist, name=song_name).first()
            if existing:
                print(f"Skipped duplicate: {artist} - {song_name}")
                return False
            row = DownloadedSong(name=song_name, artist=artist, local_path=local_path)
            db.session.add(row)
            db.session.commit()
            print(f"Added download: {artist} - {song_name}")
            return True


def create_or_append_m3u_playlist(output_folder, m3u_filename):
    print(f"Preparing clean .m3u playlist in {output_folder}...")
    # Create M3U file in glconnect folder (parent directory of glconnect/static/ytauto)
    glconnect_dir = os.path.dirname(os.path.dirname(output_folder))  # Go up from ytauto to glconnect
    m3u_path = os.path.join(glconnect_dir, m3u_filename)
    print(f"M3U file will be created at: {m3u_path}")
    
    if not os.path.exists(output_folder):
        print(f"Output folder does not exist: {output_folder}")
        return
    
    # Get only clean MP3 files (no brackets or parentheses)
    mp3_files = [filename for filename in os.listdir(output_folder) if filename.endswith(".mp3")]
    clean_files = []
    
    for filename in mp3_files:
        # Check if filename contains brackets or parentheses
        if '[' not in filename and ']' not in filename and '(' not in filename and ')' not in filename:
            clean_files.append(filename)
        else:
            print(f"Skipping file with brackets/parentheses: {filename}")
    
    print(f"Found {len(clean_files)} clean MP3 files in {output_folder}")
    clean_files.sort(key=lambda filename: filename.split(" - ")[-1].lower())
    
    # Always create a fresh playlist (overwrite mode)
    with open(m3u_path, 'w') as m3u_file:
        for filename in clean_files:
            # Generate liqfolder-style path
            liqfolder_path = f"/liqfolder/glconnect/static/ytauto/{filename}"
            m3u_file.write(liqfolder_path + "\n")
            print(f"Added {liqfolder_path} to playlist.")

    print(f"Clean playlist created: {m3u_path}")
