import os
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from glconnect import db
from glconnect.models import Writer, Book
from glconnect.forms import UploadBookForm

book = Blueprint("book", __name__)

# Define the folder where uploaded files are stored (on disk)
UPLOAD_FOLDER = os.path.join("glconnect", "static", "book_uploads")  # Corrected folder name
ABS_UPLOAD_FOLDER = os.path.join(os.getcwd(), UPLOAD_FOLDER)

# Ensure the folder exists
os.makedirs(ABS_UPLOAD_FOLDER, exist_ok=True)

@book.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_work():
    form = UploadBookForm()

    # Process the form when it is submitted
    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data
        publication_year = form.publication_year.data
        purchase_link = form.purchase_link.data
        cover_image = form.cover_image.data

        # Set the default path for the cover image if no image is uploaded
        relative_cover_path = "book_uploads/default_cover.jpg"  # Corrected path to book_uploads

        # Handle the uploaded cover image
        if cover_image:
            filename = secure_filename(cover_image.filename)
            absolute_cover_path = os.path.join(ABS_UPLOAD_FOLDER, filename)
            cover_image.save(absolute_cover_path)
            relative_cover_path = f"book_uploads/{filename}"  # Store relative path to static folder

        # Get the current writer's info (assuming they are logged in)
        writer = Writer.query.filter_by(user_id=current_user.user_id).first()
        if not writer:
            flash("You need to create a writer profile first.", "warning")
            return redirect(url_for('book_platform.setup_profile'))

        # Create the new book object and save it to the database
        new_book = Book(
            writer_id=writer.writer_id,
            title=title,
            description=description,
            publication_year=publication_year,
            purchase_link=purchase_link,
            cover_image=relative_cover_path
        )
        db.session.add(new_book)
        db.session.commit()

        flash("Book uploaded successfully!", "success")
        return redirect(url_for('writer.writer_dashboard'))

    # Render the form if it's a GET request or validation fails
    return render_template('upload_book.html', form=form)
