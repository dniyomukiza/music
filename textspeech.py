from google.cloud import texttospeech
import os

# Set the path to your service account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "textspeechdemo.json"

# Create a client
client = texttospeech.TextToSpeechClient()

# Define the text input to be synthesized
with open("news.txt", "r", encoding="utf-8") as file:
    text = file.read()
synthesis_input = texttospeech.SynthesisInput(text=text)

# Define the voice configuration
voice = texttospeech.VoiceSelectionParams(
    language_code='en-US',  # Corrected argument name
    name="en-US-Studio-O"   # Ensure this is a valid voice
)

# Define the audio configuration
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,  # Corrected argument name
    effects_profile_id=["small-bluetooth-speaker-class-device"],
    speaking_rate=1.0,  # Ensure these are float values
    pitch=1.0
)

# Perform the text-to-speech request
response = client.synthesize_speech(
    input=synthesis_input,
    voice=voice,
    audio_config=audio_config
)

# Write the output to a file
with open("news.mp3", "wb") as output:
    output.write(response.audio_content)
    print("Audio content written to file 'news.mp3'")
