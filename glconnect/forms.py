from flask_wtf import FlaskForm,RecaptchaField
from flask import flash
from .models import User
from flask_wtf.file import FileAllowed
from flask_ckeditor import CKEditorField
from wtforms import StringField, PasswordField, SubmitField,BooleanField,SelectField,TextAreaField,FileField,IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length,ValidationError,Optional
class RegistrationForm(FlaskForm):
    fname = StringField('First Name', validators=[DataRequired()], render_kw={"placeholder": "First Name"})
    lname = StringField('Last Name', validators=[DataRequired()], render_kw={"placeholder": "Last Name"})
    username = StringField(validators=[DataRequired()], render_kw={"placeholder": "Username"})
    password = StringField(validators=[DataRequired(), Length(min=2, max=20)], render_kw={"placeholder": "Password"})
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={"placeholder": "Email"})
    role = SelectField('Role', choices=[('artist', 'Artist'), ('writer', 'Writer'), ('blogger', 'Blogger'), ('other', 'Other')], default='other')
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
    submit=SubmitField('Post')
    recap=RecaptchaField()

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
    profile_picture = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
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