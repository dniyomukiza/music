import os

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
    # Define the output folder and the name of the .m3u playlist
    output_folder = os.getcwd() + "/global"
    m3u_filename = "global.m3u"

    # Create or append to the .m3u playlist
    create_or_append_m3u_playlist(output_folder, m3u_filename)

