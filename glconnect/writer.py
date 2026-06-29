import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from glconnect import db
from glconnect.models import Writer, Book
from glconnect.forms import UploadBookForm

writer = Blueprint("writer", __name__)

UPLOAD_FOLDER = os.path.join("glconnect", "static", "writer_uploads")
ABS_UPLOAD_FOLDER = os.path.join(os.getcwd(), UPLOAD_FOLDER)


def _redirect_legacy_writer_profile():
    """Legacy /writer/profile and /writer/complete-profile → Ink Studio author card."""
    return redirect(url_for('book_platform.setup_profile'), code=301)


@writer.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    return _redirect_legacy_writer_profile()


@writer.route('/profile', methods=['GET', 'POST'])
@login_required
def writer_profile():
    return _redirect_legacy_writer_profile()


os.makedirs(ABS_UPLOAD_FOLDER, exist_ok=True)


@writer.route('/dashboard')
@login_required
def writer_dashboard():
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()

    if not writer:
        flash("Set up your Ink Studio author profile to get started.", "warning")
        return redirect(url_for('book_platform.setup_profile'))

    books = Book.query.filter_by(writer_id=writer.writer_id).all()

    from glconnect.book_platform_models import BookPlatformUser, BookProject
    book_platform_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()

    book_platform_books = []
    if book_platform_user:
        book_platform_books = BookProject.query.filter_by(author_id=book_platform_user.id).all()

    return render_template(
        'writer_dashboard.html',
        writer=writer,
        books=books,
        book_platform_user=book_platform_user,
        book_platform_books=book_platform_books,
    )


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

        relative_cover_path = "writer_uploads/default_cover.jpg"

        if cover_image:
            filename = secure_filename(cover_image.filename)
            absolute_cover_path = os.path.join(ABS_UPLOAD_FOLDER, filename)
            cover_image.save(absolute_cover_path)
            relative_cover_path = f"writer_uploads/{filename}"

        writer = Writer.query.filter_by(user_id=current_user.user_id).first()
        if not writer:
            flash("Complete your Ink Studio author profile first.", "warning")
            return redirect(url_for('book_platform.setup_profile'))

        new_book = Book(
            writer_id=writer.writer_id,
            title=title,
            description=description,
            publication_year=publication_year,
            purchase_link=purchase_link,
            cover_image=relative_cover_path,
        )
        db.session.add(new_book)
        db.session.commit()

        flash("Book uploaded successfully!", "success")
        return redirect(url_for('writer.writer_dashboard'))

    return render_template('upload_book.html', form=form)


@writer.route('/view-writer/<int:writer_id>', methods=['GET'])
def view_writer(writer_id):
    writer = Writer.query.filter_by(writer_id=writer_id).first()

    if not writer:
        flash("Writer not found.", "warning")
        return redirect(url_for('routes.index'))

    books = Book.query.filter_by(writer_id=writer.writer_id).all()
    return render_template('view_writer.html', writer=writer, books=books)


@writer.route('/delete-profile', methods=['POST'])
@login_required
def delete_profile():
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()

    if not writer:
        flash("Profile not found.", "warning")
        return redirect(url_for('writer.writer_dashboard'))

    books = Book.query.filter_by(writer_id=writer.writer_id).all()
    for book in books:
        if book.cover_image and os.path.exists(os.path.join(ABS_UPLOAD_FOLDER, book.cover_image.split('/')[-1])):
            os.remove(os.path.join(ABS_UPLOAD_FOLDER, book.cover_image.split('/')[-1]))
        db.session.delete(book)

    if writer.profile_picture and os.path.exists(os.path.join(ABS_UPLOAD_FOLDER, writer.profile_picture.split('/')[-1])):
        os.remove(os.path.join(ABS_UPLOAD_FOLDER, writer.profile_picture.split('/')[-1]))

    db.session.delete(writer)

    try:
        db.session.commit()
        flash("Your profile and all associated data have been deleted.", "success")
        return redirect(url_for('routes.index'))
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('writer.writer_dashboard'))


@writer.route('/deletEbook/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()

    if not writer or book.writer_id != writer.writer_id:
        flash("You don't have permission to delete this book.", "danger")
        return redirect(url_for('writer.writer_dashboard'))

    if book.cover_image and os.path.exists(os.path.join(ABS_UPLOAD_FOLDER, book.cover_image.split('/')[-1])):
        os.remove(os.path.join(ABS_UPLOAD_FOLDER, book.cover_image.split('/')[-1]))

    db.session.delete(book)
    db.session.commit()

    flash("Book deleted successfully.", "success")
    return redirect(url_for('writer.writer_dashboard'))


@writer.route('/book-platform')
@login_required
def access_book_platform():
    return redirect(url_for('book_platform.books'))


@writer.route('/marketplace')
@login_required
def access_marketplace():
    return redirect(url_for('book_platform.marketplace'))
