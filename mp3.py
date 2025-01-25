import subprocess
import os

def convert_mp3_to_ogg(mp3_filename, output_folder):
    # This function converts a single MP3 file to OGG
    mp3_file = os.path.join(output_folder, mp3_filename)
    ogg_file = os.path.join(output_folder, mp3_filename.replace(".mp3", ".ogg"))
    
    if not os.path.exists(mp3_file):
        print(f"The file {mp3_filename} does not exist in the folder {output_folder}.")
        return
    
    # Using subprocess.run to call ffmpeg
    command = ["ffmpeg", "-i", mp3_file, "-c:a", "libvorbis", ogg_file]
    
    try:
        # Execute the command and wait for it to complete
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"Converted {mp3_file} to {ogg_file}")
    except subprocess.CalledProcessError as e:
        # Print error message if the conversion fails
        print(f"Failed to convert {mp3_file} to {ogg_file}. Error: {e.stderr.decode()}")

# Example usage
output_folder = "./"  # Replace with the actual folder path
mp3_filename = "news.mp3"  # Replace with the actual MP3 file you want to convert
convert_mp3_to_ogg(mp3_filename, output_folder)

