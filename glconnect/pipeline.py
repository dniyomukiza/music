import os
from subprocess import run
from dotenv import load_dotenv
from models import db, Song

# Load environment variables
load_dotenv()

# Path to your output folder for music files
output_folder = os.path.join(os.getcwd(), "global")

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
        # This function can run independently to convert mp3 files to ogg
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
        relative_path = file_path.split('afro/')[1]
        if ' - ' in relative_path:
            artist, song_name = relative_path.split(' - ', 1)
            song_name = song_name.replace('.ogg', '')
        else:
            artist = None
            song_name = relative_path.split('/')[-1].replace('.ogg', '')
        return artist, song_name

    @staticmethod
    def ingest_songs_from_m3u(file_path):
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
        song = Song(name=song_name, artist=artist, local_path=local_path)
        db.session.add(song)
        db.session.commit()

if __name__ == "__main__":
    # Example usage: Only renaming files
    renamer = MusicFileRenamer()
    renamer.rename_music_files(output_folder)

    # Example usage: Download and convert audio (if playlist URL is provided)
    playlist_url = os.getenv("YT_DOWNLOADS")
    if playlist_url:
        downloader = AudioDownloader(playlist_url=playlist_url, output_folder=output_folder)
        downloader.download_and_convert()

    # Example usage: Ingest songs from an M3U playlist file
    m3u_file_path = './afro.m3u'
    PlaylistIngestion.ingest_songs_from_m3u(m3u_file_path)
