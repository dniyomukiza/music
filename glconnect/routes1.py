import requests
import re,os
import json
from mailtrap import MailtrapClient, Mail, Address
from glconnect.forms import *
from glconnect.models import*
from werkzeug.security import check_password_hash
from flask import render_template, request, flash,redirect,url_for,current_app,Blueprint,session,g
from itsdangerous import URLSafeTimedSerializer
from flask_login import login_user,LoginManager

with open('/etc/glconfig.json') as json_file:
    config = json.load(json_file)
bp1 = Blueprint('routes1', __name__)
API_URL = "https://www.glc.cool/word/"
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@bp1.before_app_request
def load_logged_in_user():
    g.user_id = session.get('user_id')
@bp1.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        new_user_username = form.username.data
        new_user_password = form.password.data
        new_user_email = form.email.data
        new_user_fname = form.fname.data
        new_user_lname = form.lname.data
        new_user_role = form.role.data

        # Validate username and password
        if len(new_user_username) < 5:
            flash("Username must be at least 5 characters with one uppercase letter and a digit.", 'error')
        elif len(new_user_password) < 8 \
            or not re.search(r"[A-Z]", new_user_password) \
            or not re.search(r"[^\w\s]", new_user_password):
            flash("Password must be at least 8 characters with a capital letter and a special symbol.", 'error')

        else:
            # Create user without confirmation
            new_user = User(
                username=new_user_username,
                email=new_user_email,
                first_name=new_user_fname,
                last_name=new_user_lname,
                confirmed=False,
                role=new_user_role
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
                
                # Redirect to a page telling the user to check their email
                return redirect(url_for('routes1.check_email'))

            except Exception as e:
                db.session.rollback()
                flash("An error occurred while creating your account. Please try again.", 'error')

    return render_template('register.html', title='Register', form=form)

def send_confirmation_email(to_email, confirm_url):
    sender = config.get("SENDER_MAIL")
    receiver=to_email
    api_key = config.get("MAIL_TRAP")
    try:
        # Create the Mail object
        mail = Mail(
            sender=Address(email=sender, name="Please verify your account"),
            to=[Address(email=receiver)],
            subject="Please verify your account",
            text=(
                f"Click the link below to confirm your email:\n\n{confirm_url}"
            ),
            category="Verify email"
        )
        # Send email using Mailtrap API
        client = MailtrapClient(token=api_key)
        client.send(mail)
    except Exception as e:
        print("error occured while sinding email")


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
        username = form.username.data
        password = form.password.data
        user = User.query.filter(User.username.ilike(username)).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            session['user_id'] = user.user_id 
            flash('Login successful!', 'success')
            
            # Check for next parameter to redirect after login
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            # Default role-based redirects
            if user.role=="blogger":
                return redirect(url_for('blog.blogs'))
            elif user.role=="artist":
                return redirect(url_for('music.artist_profile'))
            elif user.role=="author":
                return redirect(url_for('writer.writer_profile'))
            elif user.role=="dreamer":
                return redirect(url_for('dream.dream_input'))
            else:
                return redirect(url_for('prof.profile'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html', title='Login', form=form)

@bp1.route('/playlist')
def playlist():
    """Render the playlist page."""
    return render_template('playlist.html')

@bp1.route('/words', methods=['GET', 'POST'])
def findwords():
    word = None

    if request.method == 'POST':
        word = request.form.get('word')
    elif request.method == 'GET':
        word = request.args.get('word')
    if word:
        word_data = word_details(word)
        return render_template('vocabulary.html', word=word_data)
    return render_template('vocabulary.html', word=None)

def word_details(word):
    try:
        url = f"{API_URL}{word}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Could not fetch details for this word"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching word details: {e}"}



@bp1.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = s.loads(token, salt='password-reset', max_age=3600)  # Token expires in 1 hour
    except Exception as e:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('routes1.reset_password_request'))

    user = User.query.filter_by(email=email).first_or_404()

    form = PasswordResetForm()

    if form.validate_on_submit():
        new_password = form.password.data

        # Validate password complexity
        if len(new_password) < 8 or not re.search(r"[A-Z]+", new_password) or not re.search(r"[_@#$]+", new_password):
            flash("Password must be at least 8 characters long, contain a capital letter, and a special symbol.", 'error')
        else:
            user.set_password(new_password)
            db.session.commit()
            flash('Your password has been reset successfully. You can now log in.', 'success')
            return redirect(url_for('routes1.login'))

    return render_template('passreset.html', title='Reset Password', form=form, token=token)

@bp1.route('/reset_request', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetRequestForm()

    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()

        if user:
            # Generate password reset token
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(user.email, salt='password-reset')
            reset_url = url_for('routes1.reset_password', token=token, _external=True)

            # Send password reset email
            send_reset_email(user.email, reset_url)
            flash("A password reset link has been sent to your email.", "info")
        else:
            flash("No account is associated with this email. Please sign up.", "error")
            return redirect(url_for('routes1.register'))

    return render_template('passreq.html', title='Reset Password', form=form)
  
def send_reset_email(to_email, reset_url):
    sender = config.get("SENDER_MAIL")
    receiver=to_email
    api_key = config.get("MAIL_TRAP")
    try:
        # Create the Mail object
        mail = Mail(
            sender=Address(email=sender, name="Reset Your Password"),
            to=[Address(email=receiver)],
            subject="Reset Your Password",
            text=(
                f"Click the link below to reset your password:\n\n{reset_url}"
            ),
            category="Reset password"
        )
        # Send email using Mailtrap API
        client = MailtrapClient(token=api_key)
        client.send(mail)
    except Exception as e:
        print("error occured while sinding email")



