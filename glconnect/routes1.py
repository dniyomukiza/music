import requests
import re,os
import json
from mailtrap import MailtrapClient, Mail, Address
from glconnect.forms import *
from glconnect.models import*
from werkzeug.security import check_password_hash
from flask import render_template, request, flash,redirect,url_for,current_app,Blueprint,session,g,jsonify
from itsdangerous import URLSafeTimedSerializer
from flask_login import login_user,LoginManager,login_required,current_user

with open('/usr/src/appdir/glconfig.json') as json_file:
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
    with open('/usr/src/appdir/glconfig.json') as json_file:
        config = json.load(json_file)
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
        from .models import WordsData
        
        # Search for the word in the local database
        word_data = WordsData.query.filter(WordsData.word == word.lower()).first()
        
        if word_data:
            # Extract English meaning properly
            meaning = "No meaning available"
            if word_data.igisobanuro_meaning and len(word_data.igisobanuro_meaning) > 0:
                last_meaning_array = word_data.igisobanuro_meaning[-1]
                if isinstance(last_meaning_array, list) and len(last_meaning_array) > 0:
                    meaning = last_meaning_array[-1]  # English is usually last
                elif isinstance(last_meaning_array, str):
                    meaning = last_meaning_array
            
            return {
                "word": word_data.word,
                "umuzi_root": word_data.umuzi_root,
                "basoma_phonetics": word_data.basoma_phonetics,
                "bandika_writing": word_data.bandika_writing,
                "icyiciro_pos": word_data.icyiciro_pos,
                "igisobanuro_meaning": word_data.igisobanuro_meaning,
                "english_meaning": meaning
            }
        else:
            return {"error": "Word not found in dictionary"}
            
    except Exception as e:
        print(f"Error in word_details: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error fetching word details: {e}"}

@bp1.route('/contribute-word', methods=['POST'])
def contribute_word():
    """Handle word contribution submissions."""
    try:
        from .models import WordContribution, WordsData, db
        from flask_login import current_user
        from datetime import datetime, timezone
        
        # Get form data
        word = request.form.get('word', '').strip()
        meaning = request.form.get('meaning', '').strip()
        example_sentence = request.form.get('example_sentence', '').strip()
        part_of_speech = request.form.get('part_of_speech', '').strip()
        phonetics = request.form.get('phonetics', '').strip()
        contributor_name = request.form.get('contributor_name', '').strip()
        
        # Validate required fields
        if not word or not meaning:
            return jsonify({
                'success': False,
                'message': 'Word and meaning are required fields.'
            }), 400
        
        # Check if word already exists in the main dictionary
        existing_word = WordsData.query.filter_by(word=word.lower()).first()
        if existing_word:
            return jsonify({
                'success': False,
                'message': f'The word "{word}" already exists in our dictionary.'
            }), 400
        
        # Check if word already has a pending contribution
        pending_contribution = WordContribution.query.filter_by(
            word=word.lower(), 
            status='pending'
        ).first()
        if pending_contribution:
            return jsonify({
                'success': False,
                'message': f'A contribution for "{word}" is already pending review.'
            }), 400
        
        # Create new contribution
        contribution = WordContribution(
            word=word.lower(),
            meaning=meaning,
            example_sentence=example_sentence if example_sentence else None,
            part_of_speech=part_of_speech if part_of_speech else None,
            phonetics=phonetics if phonetics else None,
            contributor_id=current_user.user_id if current_user.is_authenticated else None,
            contributor_name=contributor_name if contributor_name else 'Anonymous',
            status='pending'
        )
        
        db.session.add(contribution)
        db.session.commit()
        
        print(f"DEBUG: New word contribution submitted: '{word}' by {contributor_name or 'Anonymous'}")
        
        return jsonify({
            'success': True,
            'message': 'Contribution submitted successfully! It will be reviewed before being added to the dictionary.'
        })
        
    except Exception as e:
        print(f"Error in contribute_word: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred while submitting your contribution. Please try again.'
        }), 500

@bp1.route('/admin/contributions')
@login_required
def admin_contributions():
    """Admin page to review word contributions."""
    from .models import WordContribution, db
    from flask_login import current_user
    
    # Check if user is admin
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('routes1.findwords'))
    
    # Get all pending contributions
    pending_contributions = WordContribution.query.filter_by(status='pending').order_by(WordContribution.created_at.desc()).all()
    
    return render_template('admin_contributions.html', contributions=pending_contributions)

@bp1.route('/admin/approve-contribution/<int:contribution_id>', methods=['POST'])
@login_required
def approve_contribution(contribution_id):
    """Approve a word contribution and add it to the main dictionary."""
    try:
        from .models import WordContribution, WordsData, db
        from flask_login import current_user
        from datetime import datetime, timezone
        
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get the contribution
        contribution = WordContribution.query.get_or_404(contribution_id)
        
        if contribution.status != 'pending':
            return jsonify({'success': False, 'message': 'Contribution already processed'}), 400
        
        # Add to community dictionary (separate from main dictionary)
        from .community_dictionary_manager import community_dictionary_manager
        
        word_data = {
            "word": contribution.word,
            "meaning": contribution.meaning,
            "example_sentence": contribution.example_sentence or "",
            "part_of_speech": contribution.part_of_speech or "",
            "phonetics": contribution.phonetics or "",
            "contributor_name": contribution.contributor_name or "Anonymous",
            "approved_by": current_user.username or "Admin"
        }
        
        success = community_dictionary_manager.add_word(word_data)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'Error saving word to community dictionary. Word may already exist.'
            }), 500
        
        # Update contribution status
        contribution.status = 'approved'
        contribution.reviewed_at = datetime.now(timezone.utc)
        contribution.reviewer_id = current_user.user_id
        contribution.admin_notes = request.json.get('admin_notes', '') if request.is_json else ''
        
        db.session.commit()
        
        print(f"DEBUG: Contribution approved: '{contribution.word}' by admin {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Word "{contribution.word}" has been approved and added to the community dictionary.'
        })
        
    except Exception as e:
        print(f"Error in approve_contribution: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error approving contribution'}), 500

@bp1.route('/admin/reject-contribution/<int:contribution_id>', methods=['POST'])
@login_required
def reject_contribution(contribution_id):
    """Reject a word contribution."""
    try:
        from .models import WordContribution, db
        from flask_login import current_user
        from datetime import datetime, timezone
        
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get the contribution
        contribution = WordContribution.query.get_or_404(contribution_id)
        
        if contribution.status != 'pending':
            return jsonify({'success': False, 'message': 'Contribution already processed'}), 400
        
        # Update contribution status
        contribution.status = 'rejected'
        contribution.reviewed_at = datetime.now(timezone.utc)
        contribution.reviewer_id = current_user.user_id
        contribution.admin_notes = request.json.get('admin_notes', '') if request.is_json else ''
        
        db.session.commit()
        
        print(f"DEBUG: Contribution rejected: '{contribution.word}' by admin {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Contribution for "{contribution.word}" has been rejected.'
        })
        
    except Exception as e:
        print(f"Error in reject_contribution: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error rejecting contribution'}), 500

@bp1.route('/api/game-words')
def get_game_words():
    """Get random words for the matching game from the original dictionary only."""
    try:
        from .models import WordsData
        import random
        
        # Get words from original database only
        all_words = WordsData.query.all()
        
        if len(all_words) < 6:
            return jsonify({
                'success': False,
                'message': 'Not enough words in dictionary for the game. Need at least 6 words.'
            }), 400
        
        # Select 6 random words
        selected_words = random.sample(all_words, 6)
        
        # Prepare game data
        game_words = []
        for word in selected_words:
            # Extract English meaning (usually the last item in the last array)
            if word.igisobanuro_meaning and len(word.igisobanuro_meaning) > 0:
                # Get the last meaning array and extract the English translation (last item)
                last_meaning_array = word.igisobanuro_meaning[-1]
                if isinstance(last_meaning_array, list) and len(last_meaning_array) > 0:
                    meaning = last_meaning_array[-1]  # English is usually last
                elif isinstance(last_meaning_array, str):
                    meaning = last_meaning_array
                else:
                    meaning = "No meaning available"
            else:
                meaning = "No meaning available"
            
            game_words.append({
                'id': word.id,
                'word': word.word,
                'meaning': meaning,
                'part_of_speech': word.icyiciro_pos[0] if word.icyiciro_pos else None
            })
        
        # Shuffle the meanings to make it challenging
        meanings = [word['meaning'] for word in game_words]
        random.shuffle(meanings)
        
        # Debug logging removed for better performance
        
        return jsonify({
            'success': True,
            'words': game_words,
            'meanings': meanings
        })
        
    except Exception as e:
        print(f"Error in get_game_words: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error fetching words for the game: {str(e)}'
        }), 500

@bp1.route('/api/search-word')
def search_word_api():
    """API endpoint for word search."""
    word = request.args.get('word', '').strip()
    if not word:
        return jsonify({'success': False, 'message': 'No word provided'}), 400
    
    try:
        from .models import WordsData
        
        # Search for the word in the local database (case-insensitive)
        word_data = WordsData.query.filter(WordsData.word.ilike(f'%{word.lower()}%')).first()
        
        if word_data:
            # Extract English meaning properly
            meaning = "No meaning available"
            if word_data.igisobanuro_meaning and len(word_data.igisobanuro_meaning) > 0:
                last_meaning_array = word_data.igisobanuro_meaning[-1]
                if isinstance(last_meaning_array, list) and len(last_meaning_array) > 0:
                    meaning = last_meaning_array[-1]  # English is usually last
                elif isinstance(last_meaning_array, str):
                    meaning = last_meaning_array
            
            return jsonify({
                'success': True,
                'word': {
                    "word": word_data.word,
                    "umuzi_root": word_data.umuzi_root,
                    "basoma_phonetics": word_data.basoma_phonetics,
                    "bandika_writing": word_data.bandika_writing,
                    "icyiciro_pos": word_data.icyiciro_pos,
                    "igisobanuro_meaning": word_data.igisobanuro_meaning,
                    "english_meaning": meaning
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Word not found in dictionary'
            }), 404
            
    except Exception as e:
        print(f"Error in search_word_api: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error searching for word: {str(e)}'
        }), 500


@bp1.route('/api/picture-word-game')
def get_picture_word_game():
    """Get words and generate images for picture-word matching game."""
    try:
        from .models import WordsData
        import random
        import google.generativeai as genai
        import base64
        import io
        from PIL import Image
        
        # Configure Gemini
        genai.configure(api_key=current_app.config.get('GOOGLE_API_KEY'))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Get words from original database
        all_words = WordsData.query.all()
        
        if len(all_words) < 4:
            return jsonify({
                'success': False,
                'message': 'Not enough words in dictionary for the game. Need at least 4 words.'
            }), 400
        
        # Select 4 random words
        selected_words = random.sample(all_words, 4)
        
        # Prepare game data
        game_data = []
        for word in selected_words:
            # Extract English meaning (usually the last item in the last array)
            if word.igisobanuro_meaning and len(word.igisobanuro_meaning) > 0:
                # Get the last meaning array and extract the English translation (last item)
                last_meaning_array = word.igisobanuro_meaning[-1]
                if isinstance(last_meaning_array, list) and len(last_meaning_array) > 0:
                    meaning = last_meaning_array[-1]  # English is usually last
                elif isinstance(last_meaning_array, str):
                    meaning = last_meaning_array
                else:
                    meaning = "No meaning available"
            else:
                meaning = "No meaning available"
            
            # Generate image using Gemini
            try:
                prompt = f"Create a simple, clear illustration of: {meaning}. The image should be suitable for a language learning game, with a clean background and clear visual representation."
                response = model.generate_content(prompt)
                
                # For now, we'll use a placeholder approach since Gemini image generation
                # might need different handling. We'll create a simple text-based representation
                image_data = {
                    'type': 'text_placeholder',
                    'description': meaning,
                    'color': random.choice(['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'])
                }
                
            except Exception as e:
                print(f"Error generating image for {word.word}: {e}")
                # Fallback to text placeholder
                image_data = {
                    'type': 'text_placeholder',
                    'description': meaning,
                    'color': random.choice(['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'])
                }
            
            game_data.append({
                'id': word.id,
                'word': word.word,
                'meaning': meaning,
                'image': image_data,
                'part_of_speech': word.icyiciro_pos[0] if word.icyiciro_pos else None
            })
        
        # Shuffle the data to randomize positions
        random.shuffle(game_data)
        
        return jsonify({
            'success': True,
            'game_data': game_data,
            'total_words': len(game_data)
        })
        
    except Exception as e:
        print(f"Error in get_picture_word_game: {e}")
        return jsonify({
            'success': False,
            'message': 'Error generating picture-word game'
        }), 500

@bp1.route('/admin/community-dictionary')
@login_required
def community_dictionary():
    """View community dictionary (admin only)."""
    try:
        from .community_dictionary_manager import community_dictionary_manager
        
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        stats = community_dictionary_manager.get_stats()
        words = community_dictionary_manager.get_all_words()
        
        return render_template('community_dictionary.html', 
                             stats=stats, 
                             words=words)
        
    except Exception as e:
        print(f"Error in community_dictionary: {e}")
        return jsonify({'success': False, 'message': 'Error loading community dictionary'}), 500

@bp1.route('/community-dictionary')
def community_dictionary_public():
    """View community dictionary (public read-only)."""
    try:
        from .community_dictionary_manager import community_dictionary_manager
        
        stats = community_dictionary_manager.get_stats()
        words = community_dictionary_manager.get_all_words()
        
        return render_template('community_dictionary_public.html', 
                             stats=stats, 
                             words=words)
        
    except Exception as e:
        print(f"Error in community_dictionary_public: {e}")
        return jsonify({'success': False, 'message': 'Error loading community dictionary'}), 500

@bp1.route('/contribute-word')
def contribute_word_page():
    """Dedicated page for word contribution"""
    return render_template('contribute_word.html')


@bp1.route('/api/community-stats')
def get_community_stats():
    """API endpoint to get community dictionary statistics"""
    try:
        from .community_dictionary_manager import community_dictionary_manager
        
        stats = community_dictionary_manager.get_stats()
        
        # Get pending contributions count
        pending_count = WordContribution.query.filter_by(status='pending').count()
        stats['pending_words'] = pending_count
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            'total_words': 0,
            'approved_words': 0,
            'pending_words': 0,
            'error': str(e)
        })

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
    with open('/usr/src/appdir/glconfig.json') as json_file:
        config = json.load(json_file)
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



