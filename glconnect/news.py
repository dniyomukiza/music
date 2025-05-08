import os
import json
import openai
import time
from dotenv import load_dotenv
from google.cloud import texttospeech
import sys
import select

with open('/etc/glconfig.json') as json_file:
    config = json.load(json_file)

# Load your OpenAI API key from an environment variable
openai.api_key = config.get("OPENAI_AI_KEY")

# Check for API key
if not openai.api_key:
    print("API key not found. Please set the 'OPENAI_AI_KEY' environment variable.")
    exit(1)

# Set the path to your Google Cloud service account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "textspeechdemo.json"

# Create the text-to-speech client
client = texttospeech.TextToSpeechClient()

# Function to handle input with a timeout
def input_with_timeout(prompt, timeout):
    print(prompt, end=" ", flush=True)
    start_time = time.time()
    while True:
        if sys.stdin in select.select([sys.stdin], [], [], timeout)[0]:
            return input()  
        if time.time() - start_time > timeout:
            print("\nTimeout reached. No input provided.")
            return None  
        time.sleep(0.1)

news_script = "" 

while True:
    keyword = input_with_timeout("Enter a keyword for news generation (or type 'exit' to quit): ", 30)  

    if keyword is None:
        # No input provided within 1 minute
        if news_script:
            print("No input received. Generating audio from the available news text...")
            # Generate audio from the available news content
            synthesis_input = texttospeech.SynthesisInput(text=news_script)

            # Define the voice configuration
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Studio-O"
            )

            # Define the audio configuration
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                effects_profile_id=["small-bluetooth-speaker-class-device"],
                speaking_rate=1.0,
                pitch=1.0
            )

            # Perform the text-to-speech request
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Write the audio content to a file
            with open("news_audio.ogg", "wb") as output:
                output.write(response.audio_content)
                print("Audio content written to file 'news_audio.ogg'")

        print("Exiting program.")
        break

    # Exit if the user types 'exit'
    if keyword.lower() == "exit":
        print("Exiting program.")
        break

    # Process the input if it's valid (generate news)
    try:
        # Generate news using OpenAI
        ai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an experienced news reporter assistant that summarizes latest news regarding certain topics"},
                {"role": "user", "content": f"Provide a balanced article of the latest news about {keyword} with analytical perspective and potential impact. Never ever include any header titles, intro, and subtitles"}
            ],
            max_tokens=300
        )

        news_script = ai_response['choices'][0]['message']['content']
        print(news_script)

        # Save to news.txt (append mode)
        with open("news.txt", "a") as file:
            file.write(news_script)
            file.write("\n")

        print("News script saved to news.txt")

    except openai.error.OpenAIError as e:
        print(f"Error generating response from OpenAI: {e}")

    # Wait before prompting the next request
    print("Waiting for the next request...")