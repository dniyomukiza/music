from flask_wtf import FlaskForm,RecaptchaField
from flask import flash
from .models import User
from flask_wtf.file import FileAllowed
from flask_ckeditor import CKEditorField
from wtforms import StringField, PasswordField, SubmitField,BooleanField,SelectField,SelectMultipleField,TextAreaField,FileField,IntegerField,FloatField
from wtforms.validators import DataRequired, Email, EqualTo, Length,ValidationError,Optional
import os

class FileSize:
    """Validator to check file size"""
    def __init__(self, max_size_mb, message=None):
        self.max_size_mb = max_size_mb
        self.message = message or f'File size must be less than {max_size_mb}MB'

    def __call__(self, form, field):
        if field.data:
            # Check if it's a FileStorage object (Werkzeug)
            if hasattr(field.data, 'read'):
                field.data.seek(0, os.SEEK_END)
                file_size = field.data.tell()
                field.data.seek(0)  # Reset to beginning
                max_size_bytes = self.max_size_mb * 1024 * 1024
                if file_size > max_size_bytes:
                    raise ValidationError(self.message)
class RegistrationForm(FlaskForm):
    fname = StringField('First Name', validators=[DataRequired()], render_kw={"placeholder": "First Name"})
    lname = StringField('Last Name', validators=[DataRequired()], render_kw={"placeholder": "Last Name"})
    username = StringField(validators=[DataRequired()], render_kw={"placeholder": "Username"})
    password = StringField(validators=[DataRequired(), Length(min=2, max=20)], render_kw={"placeholder": "Password"})
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={"placeholder": "Email"})
    role = SelectField('Role', choices=[('artist', 'Artist'), ('author', 'Author'), ('blogger', 'Blogger'), ('podcaster', 'Podcaster'), ('freelancer', 'Freelancer'), ('other', 'Other')], default='other')
    submit = SubmitField('Sign up')
    recap=RecaptchaField()

    def validate_username(self, username):
        user_exists = User.query.filter_by(username=username.data).first()
        if user_exists:
            flash("This user already exists, just log in!")
            raise ValidationError

class LoginForm(FlaskForm):
    username = StringField(validators=[DataRequired()], render_kw={"placeholder": "Username"})
    password = StringField(validators=[DataRequired(), Length(min=2, max=20)], render_kw={"placeholder": "Password"})
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class KeywordForm(FlaskForm):
    keyword = StringField('Enter keyyword', validators=[DataRequired()])
    submit = SubmitField('Generate News')

class SlangForm(FlaskForm):
    slang = StringField('Slang Word', validators=[DataRequired()])
    original = StringField('Original Meaning', validators=[DataRequired()])
    current = StringField('Current Meaning', validators=[DataRequired()])
    example = StringField('Example Sentence', validators=[DataRequired()])
    submit = SubmitField('Submit Slang')
    recap=RecaptchaField()

    
class ContactForm(FlaskForm):
    FirstName = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    LastName = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Submit')
    recap=RecaptchaField()

class PostForm(FlaskForm):
    title=StringField("Title",validators=[DataRequired()],render_kw={"placeholder":"Blog Title"})
    content = CKEditorField('Content')
    category = SelectField('Category', choices=[
        ('', 'Select Category'),
        ('News', 'News'),
        ('Features', 'Features'),
        ('Opinion', 'Opinion'),
        ('Investigative', 'Investigative'),
        ('Technology', 'Technology'),
        ('Business', 'Business'),
        ('Culture', 'Culture'),
        ('Sports', 'Sports'),
        ('Entertainment', 'Entertainment'),
        ('Health', 'Health'),
        ('Science', 'Science'),
        ('Politics', 'Politics'),
        ('Other', 'Other')
    ], validators=[Optional()], default='')
    language = SelectField('Language', choices=[
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('it', 'Italian'),
        ('pt', 'Portuguese'),
        ('ru', 'Russian'),
        ('zh', 'Chinese'),
        ('ja', 'Japanese'),
        ('ko', 'Korean'),
        ('ar', 'Arabic'),
        ('hi', 'Hindi'),
        ('sw', 'Swahili'),
        ('rw', 'Kinyarwanda'),
        ('other', 'Other')
    ], validators=[Optional()], default='en')
    country = StringField('Country', validators=[Optional()], render_kw={"placeholder": "e.g., United States, Rwanda, Kenya"})
    submit=SubmitField('Post')

class ResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')
    recap=RecaptchaField()

class PasswordResetForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class WriterProfileForm(FlaskForm):
    writer_name = StringField('Writer Name', validators=[DataRequired()])
    bio = TextAreaField('Bio')
    profile_picture = FileField('Profile Picture', validators=[
        Optional(), 
        FileAllowed(['jpg', 'jpeg', 'png'], 'Only JPG, JPEG, and PNG images are allowed!'),
        FileSize(max_size_mb=10, message='Profile picture must be less than 10MB')
    ])
    submit = SubmitField('Save Profile')
    recap=RecaptchaField()

class UploadBookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    publication_year = IntegerField('Publication Year', validators=[DataRequired()])
    purchase_link = StringField('Purchase Link', validators=[Optional(), Length(max=300)])
    cover_image = FileField('Cover Image', validators=[Optional()])
    submit = SubmitField('Upload Book')
    recap=RecaptchaField()

class DigitalBookUploadForm(FlaskForm):
    title = StringField('Book Title', validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    genre = StringField('Genre', validators=[Optional(), Length(max=100)])
    ebook_language = SelectField(
        'Original language of your ebook',
        validators=[DataRequired()],
        choices=[],
        default='en',
    )
    extra_digital_languages = SelectMultipleField(
        'Also publish AI-translated editions (plain text)',
        validators=[Optional()],
        choices=[],
        render_kw={'class': 'form-select', 'size': '6'},
    )
    digital_book_file = FileField('Digital Book File', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'epub', 'docx', 'txt'], 'Only PDF, EPUB, DOCX, and TXT files are allowed!')
    ])
    cover_image = FileField('Cover Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Cover must be JPG, PNG, GIF, or WebP.')
    ])
    use_ai_cover = BooleanField('Generate cover with AI')
    cover_art_brief = TextAreaField('Cover art direction (for AI)', validators=[Optional(), Length(max=2000)])

    # Pricing
    digital_price = FloatField('Digital Book Price (USD)', validators=[Optional()])
    generate_audiobook = BooleanField('Generate Audiobook Version')
    audiobook_price = FloatField('Audiobook Price (USD)', validators=[Optional()])
    audiobook_tts_language = SelectField(
        'Audiobook narration language (TTS)',
        validators=[Optional()],
        choices=[],
        default='en',
        description='Voices are listed for this language. Use a language that matches your ebook text for natural narration.',
    )
    audiobook_voice = StringField('Audiobook Voice', validators=[Optional()], default='en-US-Standard-A')
    
    submit = SubmitField('List on marketplace')
    recap = RecaptchaField(validators=[])  # Make optional - can be validated conditionally

# Reviewer Registration Form
class ReviewerRegistrationForm(FlaskForm):
    reviewer_name = StringField('Reviewer Name', validators=[DataRequired(), Length(min=2, max=100)], 
                                render_kw={"placeholder": "Your professional reviewer name"})
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=1000)], 
                       render_kw={"placeholder": "Tell us about your reviewing experience"})
    profile_picture = FileField('Profile Picture', validators=[
        Optional(), 
        FileAllowed(['jpg', 'jpeg', 'png'], 'Only JPG, JPEG, and PNG images are allowed!'),
        FileSize(max_size_mb=5, message='Profile picture must be less than 5MB')
    ])
    portfolio_url = StringField('Portfolio URL', validators=[Optional(), Length(max=500)],
                               render_kw={"placeholder": "Link to your published reviews or portfolio"})
    specialties = TextAreaField('Genres You Review', validators=[Optional()],
                              render_kw={"placeholder": "e.g., Fiction, Non-fiction, Mystery, Romance (comma-separated)"})
    credentials = TextAreaField('Credentials', validators=[Optional(), Length(max=1000)],
                               render_kw={"placeholder": "Education, certifications, publications, etc."})
    default_revenue_share = FloatField('Default Revenue Share %', validators=[Optional()], default=2.5,
                                     render_kw={"placeholder": "Default percentage (e.g., 2.5)"})
    submit = SubmitField('Apply for Accreditation')
    recap = RecaptchaField()

# Book Review Submission Form
class BookReviewForm(FlaskForm):
    title = StringField('Review Title', validators=[DataRequired(), Length(min=5, max=200)],
                       render_kw={"placeholder": "Give your review a title"})
    content = CKEditorField('Review Content', validators=[DataRequired()])
    rating = IntegerField('Rating (1-5 stars)', validators=[DataRequired()],
                         render_kw={"placeholder": "1-5", "min": 1, "max": 5})
    revenue_share_percentage = FloatField('Revenue Share %', validators=[DataRequired()], default=2.5,
                                         render_kw={"placeholder": "e.g., 2.5"})
    minimum_sales_threshold = IntegerField('Minimum Sales Threshold', validators=[Optional()], default=0,
                                           render_kw={"placeholder": "Minimum sales before earning (0 = no threshold)"})
    is_public = BooleanField('Make Review Public', default=True)
    submit = SubmitField('Submit Review')

# Investment Campaign Form
class InvestmentCampaignForm(FlaskForm):
    title = StringField('Campaign Title', validators=[DataRequired(), Length(min=5, max=200)],
                       render_kw={"placeholder": "e.g., Help publish my debut novel"})
    description = CKEditorField('Campaign Description', validators=[DataRequired()],
                               render_kw={"placeholder": "Tell investors why they should invest in your book"})
    pitch_video_url = StringField('Pitch Video URL (Optional)', validators=[Optional(), Length(max=500)],
                                 render_kw={"placeholder": "YouTube, Vimeo, or other video link"})
    funding_goal = FloatField('Funding Goal (USD)', validators=[DataRequired()],
                             render_kw={"placeholder": "e.g., 5000.00", "step": "0.01"})
    minimum_investment = FloatField('Minimum Investment (USD)', validators=[DataRequired()],
                                   render_kw={"placeholder": "e.g., 50.00", "step": "0.01"})
    maximum_investment = FloatField('Maximum Investment (USD)', validators=[Optional()],
                                   render_kw={"placeholder": "e.g., 1000.00 (leave empty for no limit)", "step": "0.01"})
    revenue_share_percentage = FloatField('Revenue Share % for Investors', validators=[DataRequired()], default=25.0,
                                         render_kw={"placeholder": "Total % of sales shared with all investors (e.g., 25)"})
    return_multiplier_cap = FloatField('Return Multiplier Cap', validators=[DataRequired()], default=3.0,
                                      render_kw={"placeholder": "Maximum return (e.g., 3.0 = 3x investment)"})
    investment_period_days = IntegerField('Campaign Duration (Days)', validators=[DataRequired()], default=30,
                                         render_kw={"placeholder": "e.g., 30"})
    submit = SubmitField('Create Campaign')
    recap = RecaptchaField()

# Investment Form
class InvestmentForm(FlaskForm):
    amount = FloatField('Investment Amount (USD)', validators=[DataRequired()],
                       render_kw={"placeholder": "Enter amount", "step": "0.01"})
    submit = SubmitField('Invest Now')
    recap = RecaptchaField()