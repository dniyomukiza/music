import requests
import re,os
import smtplib
from flask_jwt_extended import jwt_required, get_jwt_identity 
from glconnect.forms import *
from glconnect.models import db,SlangWords,User
from datetime import datetime
from werkzeug.security import check_password_hash
from flask import render_template, request, flash,redirect,url_for,current_app,Blueprint
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
from flask_login import login_user, current_user,LoginManager

bp1 = Blueprint('routes1', __name__)
API_URL = "http://127.0.0.1:8001/word/"
login_manager = LoginManager()
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@bp1.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        new_user_username = form.username.data
        new_user_password = form.password.data
        new_user_email = form.email.data
        new_user_fname = form.fname.data
        new_user_lname = form.lname.data

        # Validate username and password
        if len(new_user_username) < 7 or not re.search(r"[\d]+", new_user_username) or not re.search(r"[A-Z]+", new_user_username):
            flash("Username must be at least 7 characters with one uppercase letter and a digit.", 'error')
        elif len(new_user_password) < 8 or not re.search(r"[A-Z]+", new_user_password) or not re.search(r"[_@#$]+", new_user_password):
            flash("Password must be at least 8 characters with a capital letter and a special symbol.", 'error')
        else:
            # Create user without confirmation
            new_user = User(
                username=new_user_username,
                email=new_user_email,
                first_name=new_user_fname,
                last_name=new_user_lname,
                confirmed=False
            )
            new_user.set_password(new_user_password)

            try:
                db.session.add(new_user)
                db.session.commit()

                # Generate email confirmation token
                s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
                token = s.dumps(new_user.email, salt='email-confirm')
                confirm_url = url_for('routes1.confirm_email', token=token, _external=True)

                # Send confirmation email
                send_confirmation_email(new_user.email, confirm_url)

                flash('Your account has been created! Check your email to confirm your account.', 'success')
                
                # Redirect to a page telling the user to check their email
                return redirect(url_for('routes1.check_email'))

            except Exception as e:
                db.session.rollback()
                flash("An error occurred while creating your account. Please try again.", 'error')

    return render_template('register.html', title='Register', form=form)

def send_confirmation_email(to_email, confirm_url):
    sender_email = os.getenv("MAIL_USERNAME")
    app_password = os.getenv("MAIL_PASSWORD")

    subject = "Please verify your account"
    body = f"Click the link below to confirm your email:\n\n{confirm_url}"

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(sender_email, to_email, message)
    except Exception as e:
        print(f"SMTP error: {e}")

@bp1.route('/confirm/<token>')
def confirm_email(token):
    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = s.loads(token, salt='email-confirm', max_age=3600) 
    except Exception as e:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('routes1.register'))  

    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('Your email has already been confirmed.', 'info')
    else:
        user.confirmed = True
        db.session.commit()
        flash('Your email has been confirmed. You can now log in.', 'success')

    return redirect(url_for('routes1.login'))  

@bp1.route('/check_email')
def check_email():
    return render_template('check_email.html', title='Check Email')

@bp1.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        print("validated")
        username = form.username.data
        password = form.password.data
        user = User.query.filter(User.username.ilike(username)).first()
        print(user)
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            print(f"Logged in as: {current_user.username}, authenticated: {current_user.is_authenticated}")

            # Redirect to the home page
            return redirect(url_for('routes.index'))
        else:
            flash('Invalid username or password', 'error')
    print("not validated!")
    return render_template('login.html', title='Login', form=form)

@bp1.route('/playlist')
def playlist():
    """Render the playlist page."""
    return render_template('playlist.html')

@bp1.route('/words', methods=['GET', 'POST'])
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


