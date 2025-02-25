import os
from flask import Flask
from subprocess import run
from dotenv import load_dotenv
from models import db, Song

# Load environment variables
load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "abarayon"
db.init_app(app)

# Create database tables within application context
with app.app_context():
    db.create_all()

# Path to your output folder for music files
output_folder = os.path.join(os.getcwd(), "glconnect/static/afro")

class AudioDownloader:
    def __init__(self, playlist_url=None, output_folder=None):
        self.playlist_url = playlist_url.strip() if playlist_url else None
        self.output_folder = os.path.expanduser(output_folder) if output_folder else os.getcwd()

    def prepare_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)

    def download_audio(self):
        if not self.playlist_url:
            raise ValueError("No playlist URL provided for downloading.")
        
        self.prepare_output_folder()
        command = [
            "yt-dlp",
            "-x", 
            "--audio-format", "mp3",  
            "--audio-quality", "0",
            "--yes-playlist", 
            "-o", os.path.join(self.output_folder, "%(title)s.%(ext)s"),
            self.playlist_url,
        ]
        result = run(command)
        if result.returncode == 0:
            print(f"Download completed successfully!")
        else:
            print(f"An error occurred during the download process.")

    def convert_mp3_to_ogg(self):
        for filename in os.listdir(self.output_folder):
            if filename.endswith(".mp3"):
                mp3_file = os.path.join(self.output_folder, filename)
                ogg_file = os.path.join(self.output_folder, filename.replace(".mp3", ".ogg"))
                command = ["ffmpeg", "-i", mp3_file, "-c:a", "libvorbis", ogg_file]
                result = run(command)
                if result.returncode == 0:
                    print(f"Converted {mp3_file} to {ogg_file}")
                else:
                    print(f"Failed to convert {mp3_file} to {ogg_file}")

    def download_and_convert(self):
        self.download_audio()
        self.convert_mp3_to_ogg()

class MusicFileRenamer:
    @staticmethod
    def rename_music_files(directory):
        os.chdir(directory)
        for filename in os.listdir(directory):
            if filename.endswith(".mp3") or filename.endswith(".ogg"):
                try:
                    base_name, extension = os.path.splitext(filename)
                    parts = base_name.split(" - ")
                    if len(parts) == 2:
                        artist = parts[0].strip()
                        song = parts[1].split("(")[0].strip()
                        new_filename = f"{artist} - {song}{extension}"
                        os.rename(filename, new_filename)
                        print(f"Renamed: {filename} -> {new_filename}")
                    else:
                        print(f"Skipping file (unexpected format): {filename}")
                except Exception as e:
                    print(f"Error renaming {filename}: {e}")

class PlaylistIngestion:
    @staticmethod
    def extract_song_info(file_path):
        file_path = os.path.normpath(file_path)
        keyword = os.path.join("afro", "") 
        if keyword in file_path:
            relative_path = file_path.split(keyword, 1)[1]
        else:
            print(f"Skipping file, 'afro/' not found in path: {file_path}")
            return None, None  # Gracefully handle missing paths
        
        # Extract artist and song name
        if ' - ' in relative_path:
            artist, song_name = relative_path.split(' - ', 1)
            song_name = song_name.replace('.ogg', '').strip()
        else:
            artist = None
            song_name = os.path.basename(relative_path).replace('.ogg', '').strip()
    
        return artist, song_name

    @staticmethod
    def ingest_songs_from_m3u(file_path):
        with app.app_context():  
            with open(file_path, 'r') as m3u_file:
                for line in m3u_file:
                    line = line.strip()
                    if line:
                        artist, song_name = PlaylistIngestion.extract_song_info(line)
                        song = Song(name=song_name, artist=artist, local_path=line)
                        db.session.add(song)
                db.session.commit()
            print("Songs have been ingested into the database.")

    @staticmethod
    def save_song_to_db(artist, song_name, local_path):
        with app.app_context(): 
            song = Song(name=song_name, artist=artist, local_path=local_path)
            db.session.add(song)
            db.session.commit()

# New function from file.py
def create_or_append_m3u_playlist(output_folder, m3u_filename):
    print(f"Preparing .m3u playlist in {output_folder}...")
    m3u_path = os.path.join(output_folder, m3u_filename)
    ogg_files = [filename for filename in os.listdir(output_folder) if filename.endswith(".ogg")]
    ogg_files.sort(key=lambda filename: filename.split(" - ")[-1].lower())

    file_mode = 'a' if os.path.exists(m3u_path) else 'w'
    added_songs = set()

    if file_mode == 'a':
        with open(m3u_path, 'r') as existing_playlist:
            for line in existing_playlist:
                song_identifier = os.path.basename(line.strip()).split(" - ")[-1].lower()
                added_songs.add(song_identifier)

    with open(m3u_path, file_mode) as m3u_file:
        for filename in ogg_files:
            song_identifier = filename.split(" - ")[-1].lower()
            if song_identifier not in added_songs:
                added_songs.add(song_identifier)
                ogg_file_path = os.path.join(output_folder, filename)
                m3u_file.write(os.path.abspath(ogg_file_path) + "\n")
                print(f"Added {ogg_file_path} to playlist.")
            else:
                print(f"Skipped duplicate: {filename}")

    print(f"Playlist updated: {m3u_path}")

if __name__ == "__main__":
    with app.app_context():  # Ensure all database-related actions are within an app context
        # Rename music files
        renamer = MusicFileRenamer()
        renamer.rename_music_files(output_folder)

        # Download and convert audio
        playlist_url = os.getenv("YT_DOWNLOADS")
        print("playlist", playlist_url)
        if playlist_url:
            downloader = AudioDownloader(playlist_url=playlist_url, output_folder=output_folder)
            downloader.download_and_convert()

        # Ingest songs from an M3U playlist file
        m3u_file_path = '/Users/nididier/Documents/music-1/afro.m3u'
        PlaylistIngestion.ingest_songs_from_m3u(m3u_file_path)

        # Create or append to the M3U playlist after everything is done
        create_or_append_m3u_playlist(output_folder, "afro.m3u")


