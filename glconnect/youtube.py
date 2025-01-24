import os
from subprocess import run
from dotenv import load_dotenv

class AudioDownloader:

    def __init__(self, playlist_url, output_folder):
        self.playlist_url = playlist_url.strip()
        self.output_folder = os.path.expanduser(output_folder)

    def prepare_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)

    def download_audio(self):
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


if __name__ == "__main__":
    load_dotenv()
    playlist_url = os.getenv("YT_DOWNLOADS")
    if not playlist_url:
        raise ValueError("The environment variable 'YT_DOWNLOADS' is not set or empty!")

    output_folder = os.path.join(os.getcwd(), "global")

    downloader = AudioDownloader(playlist_url=playlist_url, output_folder=output_folder)
    downloader.download_and_convert()
