import os
import json
from .models import *
from .forms import *
from dotenv import load_dotenv
from mailtrap import MailtrapClient, Mail, Address
from flask import redirect,url_for,render_template,request,flash,abort,send_from_directory
from flask import Blueprint,render_template,request,flash,redirect,url_for,send_file,current_app,session
from flask_login import current_user, login_required, logout_user
from flask_ckeditor import CKEditor,upload_success, upload_fail
load_dotenv()
with open('glconfig.json') as json_file:
    config = json.load(json_file)
blog= Blueprint("blog", __name__)
creditor = CKEditor()

@blog.route("/blogpost",methods=['GET','POST'])
@login_required
def blogpost():
    #log_web_visit()
    form = PostForm()
    if form.validate_on_submit():
        post=Post(title=form.title.data,content=form.content.data,author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your post has been created!")
        return redirect(url_for('routes.home'))
    return render_template("blogpost.html",title="New Post",form=form)

@blog.errorhandler(401)
def unauthorized(error):
    flash("You are not currently logged in")
    return redirect(url_for('routes1.login'))    

@blog.route("/blogs",methods=['GET','POST'])
def blogs():
    #log_web_visit()
    p=request.args.get('page',1, type=int)
    posts=Post.query.paginate(per_page=2,page=p)

    for post in posts:
        print(post.author)
    return render_template("blogs.html",posts=posts)

@blog.route("/post/<int:post_id>")
def update(post_id):
     #log_web_visit()
     post=Post.query.get_or_404(post_id)
     return render_template("singlepost.html",title=post.title, post=post)

@blog.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    with open('glconfig.json') as json_file:
        config = json.load(json_file)
    sender = config.get("SENDER_MAIL")
    receiver=config.get("RECEIVER_MAIL")
    api_key = config.get("MAIL_TRAP")
    if form.validate_on_submit():
        try:
            # Create the Mail object
            mail = Mail(
                sender=Address(email=sender, name="Message form GLC user"),
                to=[Address(email=receiver)],
                subject="New Contact Form Submission",
                text=(
                    f"First name: {form.FirstName.data}\n"
                    f"Last name: {form.LastName.data}\n"
                    f"Email: {form.email.data}\n"
                    f"Message: {form.message.data}"
                ),
                category="User Contact"
            )
            # Send email using Mailtrap API
            client = MailtrapClient(token=api_key)
            client.send(mail)

        except Exception as e:
            print("This is the error that occured: ",e)
            flash("An error occurred while sending the email")
        else:
            flash("Thank you for reaching out. We will get back to you ASAP.", "success")
            return redirect(url_for("blog.contact"))

    return render_template("contact.html", form=form)

@blog.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()

    # Clear session cookie
    response = redirect(url_for('routes1.login'))
    response.set_cookie('session', '', expires=0)

    # Disable caching
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    flash("You are logged out", "success")
    return response

@blog.route('/curr')
@login_required
def curr_user():
    return 'current user is '+current_user.username


@blog.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update2(post_id):
    #log_web_visit()
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    
    form = PostForm()
    if form.validate_on_submit():  
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash("Blog has been updated!")
        return redirect(url_for("blog.blogs", post_id=post.id))  
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template("blogpost.html", title="Update Post", form=form, legend="Update your blog")

@blog.route("/post/<int:post_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
         abort(403)
    db.session.delete(post)
    db.session.commit() 
    flash(" You blog post has been deleted!")
    return redirect(url_for("blog.blogs"))

# Define the UPLOAD_FOLDER and ensure it exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'glconnect', 'static', 'uploads')
# Route to serve uploaded files
@blog.route('/files/<path:filename>')
def files(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@blog.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('upload')

    if f:
        # Check file type (you can add more allowed extensions as needed)
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif',"docx"}
        file_extension = f.filename.rsplit('.', 1)[-1].lower()

        if file_extension not in allowed_extensions:
            return upload_fail(message='Invalid file type. Only image files are allowed.')

        # Define file path
        file_path = os.path.join(UPLOAD_FOLDER, f.filename)

        # Save the file
        f.save(file_path)

        # Generate URL for the uploaded file
        url = url_for('blog.files', filename=f.filename)

        # Return the success response
        return upload_success(url, filename=f.filename) 
    
    return upload_fail(message='No file uploaded', filename=None)


@blog.route("/play-audio/<int:post_id>")
def play_audio(post_id):
    post = Post.query.get_or_404(post_id)
    text = post.content  # Blog post content

    # Generate the audio file
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="EXAVITQu4vr4xnSDxMaL",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # Ensure the 'audio' directory exists
    audio_dir = os.path.join(current_app.root_path, 'static', 'audio')
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    # Create a file path to save the audio
    audio_path = os.path.join(audio_dir, f"post_{post_id}.mp3")

    # If the audio response is a generator, we need to get the content properly
    with open(audio_path, "wb") as f:
        # Assuming `audio` is a generator, you need to iterate through it or process it
        for chunk in audio:
            f.write(chunk)  # Write each chunk to the file

    # Return the audio file as a response
    return send_file(audio_path, mimetype="audio/mp3")