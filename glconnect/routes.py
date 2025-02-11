from flask import Blueprint, render_template, request, Response,flash,redirect,url_for,jsonify
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

        print("Form submitted, validating...")  # Debug print to confirm form submission

        # Validate username and password
        if len(new_user_username) < 7:
            print("Username is too short")  # Debug print for username length
        if not re.search(r"[\d]+", new_user_username):
            print("Username doesn't contain a digit")  # Debug print for digit check
        if not re.search(r"[A-Z]+", new_user_username):
            print("Username doesn't contain an uppercase letter")  # Debug print for uppercase check

        if len(new_user_username) < 7 or not re.search(r"[\d]+", new_user_username) or not re.search(r"[A-Z]+", new_user_username):
            flash("Username must be at least 7 characters with one uppercase letter and a digit.", 'error')
        elif len(new_user_password) < 8:
            print("Password is too short")  # Debug print for password length
        if not re.search(r"[A-Z]+", new_user_password):
            print("Password doesn't contain an uppercase letter")  # Debug print for uppercase check
        if not re.search(r"[_@#$]+", new_user_password):
            print("Password doesn't contain a special symbol")  # Debug print for special symbol check

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
    word = request.args.get('word')  # Get the word from the query parameter
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
            created_by=user_id,  # Store the user ID
            created_at=datetime.now().isoformat(),  # Current timestamp
            approved=False  # Slang needs to be reviewed (not approved yet)
        )

        # Add the new slang entry to the database
        db.session.add(new_slang)
        db.session.commit()

        flash('Slang submitted for approval!', 'success')
        return redirect(url_for('bp.add_slang'))  # Redirect to the form after submission

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

def stream_icecast():
    """Get the audio stream from Icecast."""
    url = 'http://localhost:8000/station'
    while True:
        with requests.get(url, stream=True) as r:
            if r.status_code == 200:
                for chunk in r.iter_content(chunk_size=1024):
                    yield chunk
        time.sleep(0.5)
