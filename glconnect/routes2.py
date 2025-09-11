import os
import json
import openai
from glconnect.forms import *
from flask import render_template, request, Blueprint, send_from_directory
from glconnect.search import SongSearcher
from google.cloud import texttospeech

# Load your OpenAI API key from environment variables
openai.api_key = os.getenv("OPENAI_AI_KEY")
bp2 = Blueprint('routes2', __name__)

# Check for API key
if not openai.api_key:
    print("API key not found. Please set the 'OPENAI_AI_KEY' in glconfig.json.")
    exit(1)

# Get Google API key from environment variables
google_api_key = os.getenv("GOOGLE_API_KEY")

# Get TTS credentials path from environment variables
tts_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json")

# Create the text-to-speech client (lazy initialization)
client = None
@bp2.route("/news", methods=["GET", "POST"])
def news():
    form = KeywordForm()
    audio_file_path = None
    news_file_path = None  
    
    if form.validate_on_submit():
        keyword = form.keyword.data
        print(f"Form keyword: {form.keyword.data}")
        
        try:
            # Step 1: Generate news content using OpenAI API
            ai_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an experienced news reporter assistant that summarizes the latest news regarding certain topics."},
                    {"role": "user", "content": f"Provide a balanced article of the latest news about {keyword} with an analytical perspective and potential impact. Never include any header titles, intro, and subtitles."}
                ],
                max_tokens=300
            )
            news_script = ai_response['choices'][0]['message']['content']
            
            # Step 2: Save the generated news content to news.txt
            static_folder = os.path.join(os.getcwd(), 'glconnect/static')
            if not os.path.exists(static_folder):
                os.makedirs(static_folder)

            news_file_path = os.path.join(static_folder, 'news.txt')
            with open(news_file_path, 'w') as news_file:
                news_file.write(news_script)
            print(f"News text saved to {news_file_path}")

            # Step 3: Generate speech using Google Cloud TTS
            # Load credentials from file and pass to client
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(tts_credentials_path)
            client = texttospeech.TextToSpeechClient(credentials=credentials)
            synthesis_input = texttospeech.SynthesisInput(text=news_script)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-D"
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            # Initialize client if needed
            if client is None:
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(tts_credentials_path)
                client = texttospeech.TextToSpeechClient(credentials=credentials)
            
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            # Step 4: Save the generated audio to news_audio.mp3
            audio_file_path = os.path.join(static_folder, 'news_audio.mp3')
            with open(audio_file_path, "wb") as audio_file:
                audio_file.write(response.audio_content)
            print(f"Audio saved to {audio_file_path}")
        
        except openai.error.OpenAIError as e:
            print(f"Error generating response from OpenAI: {e}")
        except Exception as e:
            print(f"Error generating speech: {e}")
    
    # Ensure audio file exists before passing to template (only if audio_file_path is not None)
    audio_file_ready = audio_file_path and os.path.exists(audio_file_path)
    
    # Convert file path to URL for web serving
    audio_file_url = None
    if audio_file_ready:
        # Convert absolute path to relative URL for static serving
        audio_file_url = f"/static/{os.path.basename(audio_file_path)}"
    
    # Render template and pass paths for news and audio
    return render_template(
        "newsgen.html",
        form=form,
        audio_file=audio_file_url,
        audio_file_path=audio_file_path if audio_file_ready else None,
        news_file_path=news_file_path
    )

@bp2.route('/static/<filename>')
def serve_audio(filename):
    """Serve audio files from the static directory"""
    static_folder = os.path.join(os.getcwd(), 'glconnect/static')
    return send_from_directory(static_folder, filename)

