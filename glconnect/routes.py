from flask import Blueprint, render_template, request, Response,flash,redirect,url_for,send_file
from flask_jwt_extended import jwt_required, get_jwt_identity 
from glconnect.search import SongSearcher
from glconnect.forms import *
from glconnect.models import db,SlangWords,User
from datetime import datetime
from werkzeug.security import check_password_hash
from flask_login import login_user, current_user,LoginManager
import requests
import time,re
from re import search
import os
import openai
import time
from dotenv import load_dotenv
from google.cloud import texttospeech



login_manager = LoginManager()
bp = Blueprint('routes', __name__)
API_URL = "http://127.0.0.1:8001/word/"

@bp.route('/')
def index():
    """Render the home page."""
    return render_template('home.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        new_user_username = form.username.data
        new_user_password = form.password.data
        new_user_email = form.email.data
        new_user_phone = form.phone.data
        new_user_fname = form.fname.data
        new_user_lname = form.lname.data

        print("Form submitted, validating...")  

        # Validate username and password
        if len(new_user_username) < 7:
            print("Username is too short")
        if not re.search(r"[\d]+", new_user_username):
            print("Username doesn't contain a digit")
        if not re.search(r"[A-Z]+", new_user_username):
            print("Username doesn't contain an uppercase letter") 

        if len(new_user_username) < 7 or not re.search(r"[\d]+", new_user_username) or not re.search(r"[A-Z]+", new_user_username):
            flash("Username must be at least 7 characters with one uppercase letter and a digit.", 'error')
        elif len(new_user_password) < 8:
            print("Password is too short")
        if not re.search(r"[A-Z]+", new_user_password):
            print("Password doesn't contain an uppercase letter")
        if not re.search(r"[_@#$]+", new_user_password):
            print("Password doesn't contain a special symbol")

        if len(new_user_password) < 8 or not re.search(r"[A-Z]+", new_user_password) or not re.search(r"[_@#$]+", new_user_password):
            flash("Password must be at least 8 characters with a capital letter and a special symbol.", 'error')
        else:
            # Create a new user and set the password
            new_user = User(
                username=new_user_username,
                email=new_user_email,
                phone=new_user_phone,
                first_name=new_user_fname,
                last_name=new_user_lname
            )

            # Set the hashed password
            new_user.set_password(new_user_password)

            db.session.add(new_user)
            db.session.commit()

            flash('Your account has been successfully created! Please login below.', 'success')
            return redirect(url_for('routes.login'))

    return render_template('register.html', title='Register', form=form)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username.lower()).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            print(f"Logged in as: {current_user.username}, authenticated: {current_user.is_authenticated}")

            # Redirect to the home page
            return redirect(url_for('routes.index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html', title='Login', form=form)

@bp.route('/words', methods=['GET', 'POST'])
def findwords():
    word = request.args.get('word')
    if word:
        # Call the external API to get word details
        word_data = word_details(word)
        # Pass the word data to the template
        return render_template('vocabulary.html', word=word_data)
    return render_template('vocabulary.html', word=None)

def word_details(word):
    try:
        # Make the API request
        response = requests.get(API_URL + word)
        
        # If the request was successful, return the JSON response
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Could not fetch details for this word"}
    except requests.exceptions.RequestException as e:
        # In case of an error with the API request
        return {"error": f"Error fetching word details: {e}"}
'''
@bp.route("/slang", methods=["GET"])
def get_slangform():
    return render_template("slang.html")  '''

@bp.route("/slang", methods=["GET", "POST"])
@jwt_required() 
def add_slang():
    form = SlangForm()

    # Check if the form was submitted and validated
    if form.validate_on_submit():
        slang_word = form.slang.data
        original = form.original.data
        current = form.current.data
        example = form.example.data

        # Get the user ID from JWT
        user_id = get_jwt_identity()

        # Check if the slang already exists in the database
        if SlangWords.query.filter_by(slang=slang_word).first():
            flash('Slang already exists', 'error')
            return redirect(url_for('bp.add_slang'))

        # Create a new slang word entry to be submitted for approval
        new_slang = SlangWords(
            slang=slang_word,
            original=original,
            current=current,
            example=example,
            created_by=user_id,
            created_at=datetime.now().isoformat(), 
            approved=False 
        )

        # Add the new slang entry to the database
        db.session.add(new_slang)
        db.session.commit()

        flash('Slang submitted for approval!', 'success')
        return redirect(url_for('bp.add_slang')) 

    # Render the form template
    return render_template('slang.html', form=form)

@bp.route('/playlist')
def playlist():
    """Render the playlist page."""
    return render_template('playlist.html')

@bp.route('/stream')
def stream():
    """Stream content from Icecast."""
    return Response(
        stream_icecast(),
        content_type='audio/ogg',
        status=200
    )

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

# Load environment variables
load_dotenv()

# Load your OpenAI API key from an environment variable
openai.api_key = os.getenv("OPENAI_AI_KEY")

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

def stream_icecast():
    """Get the audio stream from Icecast."""
    url = 'http://localhost:8000/station'
    while True:
        with requests.get(url, stream=True) as r:
            if r.status_code == 200:
                for chunk in r.iter_content(chunk_size=1024):
                    yield chunk
        time.sleep(0.5)
