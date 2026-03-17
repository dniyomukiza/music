import os
import json
from sqlalchemy import create_engine, Column, String, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

with open('glconfig.json', 'r') as config_file:
    config = json.load(config_file)
    db_url = config.get('DB_URL')

Base = declarative_base()

# Connect to PostgreSQL using the URL from the config file
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

class Song(Base):
    __tablename__ = 'songs'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    artist = Column(String, nullable=True)
    local_path = Column(String, nullable=True)
    spotify_id = Column(String, nullable=True)
    is_available_on_spotify = Column(Boolean, default=False)

# Create all tables
Base.metadata.create_all(engine)

# Function to extract artist and song name from the file path
def extract_song_info(file_path):
    # Split the path after 'afro/'
    relative_path = file_path.split('afro/')[1]
    
    # If there is no ' - ' in the relative path
    if ' - ' in relative_path:
        artist, song_name = relative_path.split(' - ', 1)
        song_name = song_name.replace('.ogg', '')
    else:
        # If no ' - ' is found
        artist = None
        song_name = relative_path.split('/')[-1].replace('.ogg', '')
    
    return artist, song_name

# Function to ingest songs into the database from an M3U file
def ingest_songs_from_m3u(file_path):
    with open(file_path, 'r') as m3u_file:
        for line in m3u_file:
            line = line.strip()
            if line:
                artist, song_name = extract_song_info(line)
                song = Song(name=song_name, artist=artist, local_path=line)
                session.add(song)
        session.commit()
    print("Songs have been ingested into the database.")

# Example usage
m3u_file_path = './afro.m3u'
ingest_songs_from_m3u(m3u_file_path)


