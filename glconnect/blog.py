import os
from datetime import datetime,timedelta
from flask import Flask,redirect,url_for,render_template,request,flash,abort,send_from_directory
from flask import Blueprint,render_template,request,flash,redirect,url_for,session,jsonify
from flask_login import login_user, current_user, login_required, logout_user,LoginManager,login_manager
from .models import *
from .forms import *
from re import search
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_ckeditor import CKEditor,upload_success, upload_fail

import smtplib
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
        return redirect(url_for('routes.index'))
    return render_template("blogpost.html",title="New Post",form=form)

@blog.errorhandler(401)
def unauthorized(error):
    flash("You are not currently logged in")
    return redirect(url_for('routes1.login'))    

@blog.route("/blogs",methods=['GET','POST'])
def blogs():
    #log_web_visit()
    posts=Post.query.all()
    for post in posts:
        print(post.author)
    return render_template("blogs.html",posts=posts)

@blog.route('/logout')
@login_required
def logout():
    #log_web_visit()
    logout_user
    flash("You are logged out")
    return redirect(url_for('routes1.login'))

@blog.route('/curr')
@login_required
def curr_user():
    return 'current user is '+current_user.username

@blog.route("/post/<int:post_id>")
def update(post_id):
     #log_web_visit()
     post=Post.query.get_or_404(post_id)
     return render_template("singlepost.html",title=post.title, post=post)

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

@blog.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        def send_email():
    
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()

            server.login(os.environ.get("CONF_EMAIL2"), os.environ.get("CONF_CODE2"))

            # Create the email content
            subject = 'NEW EMAIL FROM A CUSTOMER'
            body = f"First name: {form.firstName.data} \n Last name:  {form.lastName.data} \n Email:  {form.email.data}\n Message: {form.message.data}"
            message = MIMEMultipart()
            message['From'] =form.email.data
            message['Subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            # Send the email
            server.sendmail(form.email.data, os.environ.get("CONF_EMAIL"), message.as_string())

            # Close the server connection
            server.quit()
        send_email()  
        flash("Thank you for reaching out, we will get back to you as soon as possible")
        form.firstName.data = ''
        form.lastName.data = ''
        form.email.data = ''
        form.message.data = ''  
    return render_template("contact.html",form=form)


# Define the UPLOAD_FOLDER and ensure it exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'glconnect', 'static', 'uploads')
print(f"File saved at: {UPLOAD_FOLDER}")

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