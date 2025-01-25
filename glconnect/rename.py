import os

def rename_music_files(directory):
    # Change to the target directory
    os.chdir(directory)
    
    # Loop through all files in the directory
    for filename in os.listdir(directory):
        # Process only .mp3 and .ogg files
        if filename.endswith(".mp3") or filename.endswith(".ogg"):
            try:
                # Extract the base name without extension
                base_name, extension = os.path.splitext(filename)
                
                # Split by " - " to separate artist and song
                parts = base_name.split(" - ")
                
                if len(parts) == 2:  # Ensure the file follows the expected format
                    artist = parts[0].strip()
                    song = parts[1].strip()
                    
                    # Remove unwanted parts from the song name (e.g., "(Official Video)")
                    song = song.split("(")[0].strip()
                    
                    # Create the new filename
                    new_filename = f"{artist} - {song}{extension}"
                    
                    # Rename the file
                    os.rename(filename, new_filename)
                    print(f"Renamed: {filename} -> {new_filename}")
                else:
                    print(f"Skipping file (unexpected format): {filename}")
            
            except Exception as e:
                print(f"Error renaming {filename}: {e}")

# Replace this with the path to your 'afro' folder
music_directory = "~/Desktop/music/static/songs"

rename_music_files(music_directory)
