import os
from .models import db, Song

class SongSearcher:
    def __init__(self, query):
        self.query = query

    def search_song_in_database(self):
        # Ensure you're using the app context when accessing the database
        song = db.session.query(Song).filter(Song.name.ilike(f"%{self.query}%")).first()
        return song

    def play_song(self, song):
        if not song:
            return None  

        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        song_path = os.path.join("static", "afro", f"{song.artist} - {song.name}.mp3")

        # Check if the file exists
        if not os.path.exists(song_path):
            print(f"Song file not found at: {song_path}")
            return None
        
        return song_path

    def search_and_play_song(self):
        # Search for the song in the database
        song = self.search_song_in_database()

        if song:
            # Generate the song path
            song_path = self.play_song(song)
            if song_path:
                print("song path from songsearcher",song_path)
                return song.name, song.artist, f"afro/{song.artist} - {song.name}.mp3"
            else:
                print("Song found in database, but file not found in static/songs directory.")
        else:
            print("No song found matching your query.")
        return None
