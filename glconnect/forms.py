from flask_wtf import FlaskForm
from flask import flash
from datetime import datetime
from .models import User
from wtforms import StringField, PasswordField, SubmitField,BooleanField,DateField,SelectField,IntegerField,TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp,ValidationError

class RegistrationForm(FlaskForm):
    fname = StringField('First Name', validators=[DataRequired()], render_kw={"placeholder": "First Name"})
    lname = StringField('Last Name', validators=[DataRequired()], render_kw={"placeholder": "Last Name"})
    username = StringField(validators=[DataRequired()], render_kw={"placeholder": "Username"})
    password = StringField(validators=[DataRequired(), Length(min=2, max=20)], render_kw={"placeholder": "Password"})
    email = StringField('Email', validators=[DataRequired(), Email()], render_kw={"placeholder": "Email"})
    phone = StringField('Phone', validators=[DataRequired(), Regexp(r'^\d{10}$', message="Phone number must be 10 digits")], render_kw={"placeholder": "Phone"})
    submit = SubmitField('Sign up')

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

class OTPForm(FlaskForm):
    otp_code = StringField('Verification Code', validators=[DataRequired()])
    submit = SubmitField('Submit')

class SlangForm(FlaskForm):
    slang = StringField('Slang Word', validators=[DataRequired()])
    original = StringField('Original Meaning', validators=[DataRequired()])
    current = StringField('Current Meaning', validators=[DataRequired()])
    example = StringField('Example Sentence', validators=[DataRequired()])
    submit = SubmitField('Submit Slang')

class ReservationForm(FlaskForm):
    location = StringField('Location', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')
    start_time = SelectField('Start Time', validators=[DataRequired()])
    end_time = SelectField('End Time', validators=[DataRequired()])
    message = TextAreaField('Message')

    def validate_end_time(self, end_time):
        start_time_str = self.start_time.data
        end_time_str = end_time.data
        if not start_time_str or not end_time_str:
            return

        start_time = datetime.strptime(start_time_str, '%I:%M %p').time()
        end_time = datetime.strptime(end_time_str, '%I:%M %p').time()

        start_dt = datetime.combine(self.date.data, start_time)
        end_dt = datetime.combine(self.date.data, end_time)

        if end_dt <= start_dt:
            raise ValidationError('End time must be after start time')

        # Calculate total duration in minutes
        duration_minutes = (end_dt - start_dt).seconds // 60

        if duration_minutes > 300:  # 300 minutes = 5 hours
            raise ValidationError('Reservation duration cannot exceed 5 hours')
    
class ContactForm(FlaskForm):
    FirstName = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    LastName = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=15)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Submit')