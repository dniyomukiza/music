import os
import openai
from glconnect.forms import *
from glconnect.routes import bp
from dotenv import load_dotenv
from flask import render_template, request
from glconnect.search import SongSearcher
from google.cloud import texttospeech

# Load environment variables
load_dotenv()
# Load your OpenAI API key from an environment variable
openai.api_key = os.getenv("OPENAI_AI_KEY")

@bp.route('/search', methods=['GET', 'POST'])
def search():
    error_message = None
    song_result = None

    if request.method == 'POST':
        query = request.form['song_query']
        song_searcher = SongSearcher(query)
        result = song_searcher.search_and_play_song()

        if result is None:  # No song found
            error_message = "No song found matching your query."
        else:
            song_result = {
                'name': result[0],
                'artist': result[1],
                'path': result[2]  
            }

    return render_template('search.html', error_message=error_message, song_result=song_result)



# Check for API key
if not openai.api_key:
    print("API key not found. Please set the 'OPENAI_AI_KEY' environment variable.")
    exit(1)

# Set the path to your Google Cloud service account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "textspeechdemo.json"

# Create the text-to-speech client
client = texttospeech.TextToSpeechClient()
@bp.route("/news", methods=["GET", "POST"])
def news():
    form = KeywordForm()  # Assuming you have a form to collect keywords
    audio_file_path = None
    news_file_path = None  # Placeholder for news file path
    
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
            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=news_script)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-D"
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

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
    
    # Render template and pass paths for news and audio
    return render_template(
        "newsgen.html",
        form=form,
        audio_file_path=audio_file_path if audio_file_ready else None,
        news_file_path=news_file_path
    )

