import os
from flask import Blueprint, render_template, redirect, url_for, flash, request,jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from glconnect import db
from glconnect.models import Writer, Book
from glconnect.forms import WriterProfileForm, UploadBookForm

writer = Blueprint("writer", __name__)

# Define the folder where uploaded files are stored (on disk)
UPLOAD_FOLDER = os.path.join("glconnect", "static", "writer_uploads")  # Relative path for saving
ABS_UPLOAD_FOLDER = os.path.join(os.getcwd(), UPLOAD_FOLDER)  # Absolute path for saving


@writer.route('/profile', methods=['GET', 'POST'])
@login_required
def writer_profile():
    form = WriterProfileForm()
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()  # Get the first existing writer for the user

    if form.validate_on_submit():
        writer_name = form.writer_name.data
        bio = form.bio.data
        profile_pic = form.profile_picture.data
        relative_path = writer.profile_picture  # Default to the current picture if no new upload

        # Check if a new profile picture is uploaded
        if profile_pic:
            filename = secure_filename(profile_pic.filename)
            absolute_path = os.path.join(ABS_UPLOAD_FOLDER, filename)
            profile_pic.save(absolute_path)
            relative_path = f"writer_uploads/{filename}"  # Path relative to /static/

        # Update the existing writer's details
        if writer:
            writer.writer_name = writer_name
            writer.bio = bio
            writer.profile_picture = relative_path  # Update profile picture

            try:
                db.session.commit()
                flash("Profile updated successfully!", "success")
                return redirect(url_for('writer.writer_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred: {e}", "danger")
        else:
            # If no writer exists for the user, create a new record
            new_writer = Writer(
                user_id=current_user.user_id,
                writer_name=writer_name,
                bio=bio,
                profile_picture=relative_path
            )
            db.session.add(new_writer)

            try:
                db.session.commit()
                flash("Profile saved successfully!", "success")
                return redirect(url_for('writer.writer_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred: {e}", "danger")

    return render_template('writer_profile.html', form=form, writer=writer)

# Ensure the folder exists
os.makedirs(ABS_UPLOAD_FOLDER, exist_ok=True)




@writer.route('/dashboard')
@login_required
def writer_dashboard():
    # Get the current writer's info
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()
    
    if not writer:
        flash("Please create a writer profile first.", "warning")
        return redirect(url_for('writer.writer_profile'))

    # Fetch books uploaded by this writer
    books = Book.query.filter_by(writer_id=writer.writer_id).all()
    
    # Check if user has book platform profile
    from glconnect.book_platform_models import BookPlatformUser
    book_platform_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Get book platform books if user has profile
    book_platform_books = []
    if book_platform_user:
        from glconnect.book_platform_models import BookProject
        book_platform_books = BookProject.query.filter_by(author_id=book_platform_user.id).all()

    # Render the writer's dashboard and pass the writer and books to the template
    return render_template('writer_dashboard.html', 
                         writer=writer, 
                         books=books,
                         book_platform_user=book_platform_user,
                         book_platform_books=book_platform_books)



@writer.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_work():
    form = UploadBookForm()

    if form.validate_on_submit():
        title = form.title.data
        description = form.description.data
        publication_year = form.publication_year.data
        purchase_link = form.purchase_link.data
        cover_image = form.cover_image.data

        relative_cover_path = "writer_uploads/default_cover.jpg"  # Default cover image path

        # Handle cover image upload
        if cover_image:
            filename = secure_filename(cover_image.filename)
            absolute_cover_path = os.path.join(ABS_UPLOAD_FOLDER, filename)
            cover_image.save(absolute_cover_path)
            relative_cover_path = f"writer_uploads/{filename}"  # Relative path to static folder

        # Get the writer's information (assumes the writer is logged in)
        writer = Writer.query.filter_by(user_id=current_user.user_id).first()
        if not writer:
            flash("You need to create a writer profile first.", "warning")
            return redirect(url_for('writer.writer_profile'))

        # Create a new book record and save it to the database
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
        return redirect(url_for('writer.writer_dashboard'))  # Redirect to the dashboard to view the uploaded book

    return render_template('upload_book.html', form=form)


@writer.route('/view-writer/<int:writer_id>', methods=['GET'])
def view_writer(writer_id):
    # Fetch the writer's info based on the writer_id
    writer = Writer.query.filter_by(writer_id=writer_id).first()
    
    if not writer:
        flash("Writer not found.", "warning")
        return redirect(url_for('routes.home'))

    # Fetch books uploaded by this writer
    books = Book.query.filter_by(writer_id=writer.writer_id).all()

    # Render the writer's profile page and pass the writer and books to the template
    return render_template('view_writer.html', writer=writer, books=books)

@writer.route('/delete-profile', methods=['POST'])
@login_required
def delete_profile():
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()

    if not writer:
        flash("Profile not found.", "warning")
        return redirect(url_for('writer.writer_dashboard'))

    # Remove associated books
    books = Book.query.filter_by(writer_id=writer.writer_id).all()
    for book in books:
        # Optionally, remove cover images from file system
        if book.cover_image and os.path.exists(os.path.join(ABS_UPLOAD_FOLDER, book.cover_image.split('/')[-1])):
            os.remove(os.path.join(ABS_UPLOAD_FOLDER, book.cover_image.split('/')[-1]))
        db.session.delete(book)

    # Remove the profile picture from file system
    if writer.profile_picture and os.path.exists(os.path.join(ABS_UPLOAD_FOLDER, writer.profile_picture.split('/')[-1])):
        os.remove(os.path.join(ABS_UPLOAD_FOLDER, writer.profile_picture.split('/')[-1]))

    # Delete the writer profile
    db.session.delete(writer)
    
    try:
        db.session.commit()
        flash("Your profile and all associated data have been deleted.", "success")
        return redirect(url_for('routes.home'))  # Redirect to home or another page
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('writer.writer_dashboard'))
@writer.route('/delete-book/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    # Fetch the book to be deleted using the book_id
    book = Book.query.get_or_404(book_id)

    # Fetch the writer associated with the logged-in user
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()

    # Check if the current logged-in user is the writer who uploaded this book
    if not writer or book.writer_id != writer.writer_id:
        flash("You don't have permission to delete this book.", "danger")
        return redirect(url_for('writer.writer_dashboard'))

    # Optionally, delete the cover image file from the filesystem
    if book.cover_image and os.path.exists(os.path.join(ABS_UPLOAD_FOLDER, book.cover_image.split('/')[-1])):
        os.remove(os.path.join(ABS_UPLOAD_FOLDER, book.cover_image.split('/')[-1]))

    # Delete the book from the database
    db.session.delete(book)
    db.session.commit()

    flash("Book deleted successfully.", "success")
    return redirect(url_for('writer.writer_dashboard'))

@writer.route('/book-platform')
@login_required
def access_book_platform():
    """Redirect to book platform dashboard - writers can access directly"""
    # Writers can now access book platform directly without separate profile
    return redirect(url_for('book_platform.dashboard'))

@writer.route('/marketplace')
@login_required
def access_marketplace():
    """Access marketplace from writer platform"""
    return redirect(url_for('book_platform.marketplace'))
