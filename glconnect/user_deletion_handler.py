"""
Utility functions for handling user deletion with proper cascade cleanup
"""
from glconnect import db
from glconnect.models import User, Writer, Book
from glconnect.book_platform_models import (
    BookPlatformUser, BookProject, BookCollaboration,
    BookComment, CollaborationInvitation, BookPurchase, BookSale,
    RealtimeSession, BookAnalytics, BookNotification
)
from glconnect.book_utils import delete_book_chapter_version_graph_for_project
import os


def delete_user_and_all_data(user_id, *, commit: bool = True):
    """
    Safely delete a user and all associated data including:
    - Writer profiles and books
    - BookPlatformUser profile and all Ink Studio books
    - All related records (collaborations, comments, etc.)
    
    Args:
        user_id: The user_id to delete
        
    Returns:
        dict: Result with success status and message
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': f'User with ID {user_id} not found'}
        
        user_username = user.username
        
        # 1. Delete Writer profile and associated books
        writers = Writer.query.filter_by(user_id=user_id).all()
        for writer in writers:
            # Delete books associated with this writer
            books = Book.query.filter_by(writer_id=writer.writer_id).all()
            for book in books:
                # Delete cover images from filesystem
                if book.cover_image:
                    try:
                        cover_path = os.path.join(os.getcwd(), 'glconnect', 'static', book.cover_image)
                        if os.path.exists(cover_path):
                            os.remove(cover_path)
                    except Exception as e:
                        print(f"Error deleting cover image {book.cover_image}: {e}")
                db.session.delete(book)
            
            # Delete profile picture from filesystem
            if writer.profile_picture:
                try:
                    pic_path = os.path.join(os.getcwd(), 'glconnect', 'static', writer.profile_picture)
                    if os.path.exists(pic_path):
                        os.remove(pic_path)
                except Exception as e:
                    print(f"Error deleting profile picture {writer.profile_picture}: {e}")
            
            db.session.delete(writer)
        
        # 2. Delete BookPlatformUser and all Ink Studio data
        bp_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
        if bp_user:
            bp_user_id = bp_user.id
            
            # Get all books authored by this user
            authored_books = BookProject.query.filter_by(author_id=bp_user_id).all()
            
            for book in authored_books:
                # Delete all associated data for each book
                cleanup_book_data(book.id)
                
                # Delete book files (cover, digital file, audiobook)
                cleanup_book_files(book)
                
                db.session.delete(book)
            
            # Delete collaborations where user is collaborator
            collaborations = BookCollaboration.query.filter_by(collaborator_id=bp_user_id).all()
            for collab in collaborations:
                db.session.delete(collab)
            
            # Delete comments made by this user
            comments = BookComment.query.filter_by(commenter_id=bp_user_id).all()
            for comment in comments:
                db.session.delete(comment)
            
            # Delete purchases made by this user (optional - might want to keep for records)
            purchases = BookPurchase.query.filter_by(buyer_id=bp_user_id).all()
            for purchase in purchases:
                # Delete associated sales
                sales = BookSale.query.filter_by(purchase_id=purchase.id).all()
                for sale in sales:
                    db.session.delete(sale)
                db.session.delete(purchase)
            
            # Delete sales made by this user
            sales = BookSale.query.filter_by(seller_id=bp_user_id).all()
            for sale in sales:
                db.session.delete(sale)
            
            # Delete invitations sent by this user
            invitations = CollaborationInvitation.query.filter_by(invited_by_id=bp_user_id).all()
            for invitation in invitations:
                db.session.delete(invitation)
            
            # Notifications for this author; book analytics are per book_project (removed with books)
            BookNotification.query.filter_by(user_id=bp_user_id).delete()
            
            # Delete profile picture
            if bp_user.profile_picture:
                try:
                    pic_path = os.path.join(os.getcwd(), 'glconnect', 'static', bp_user.profile_picture)
                    if os.path.exists(pic_path):
                        os.remove(pic_path)
                except Exception as e:
                    print(f"Error deleting BookPlatformUser profile picture: {e}")
            
            db.session.delete(bp_user)
        
        # 3. Finally delete the user
        db.session.delete(user)

        if commit:
            db.session.commit()
        else:
            db.session.flush()

        return {
            'success': True,
            'message': f'User {user_username} and all associated data deleted successfully'
        }

    except Exception as e:
        if commit:
            db.session.rollback()
        return {
            'success': False,
            'message': f'Error deleting user: {str(e)}'
        }


def cleanup_book_data(book_id):
    """Clean up all data associated with a book"""
    try:
        # Real time sessions
        RealtimeSession.query.filter_by(book_project_id=book_id).delete()
        
        # Comments (cascade should handle this, but being explicit)
        BookComment.query.filter_by(book_project_id=book_id).delete()
        
        # Invitations via collaborations
        collab_ids_subq = db.session.query(BookCollaboration.id).filter_by(book_project_id=book_id).subquery()
        CollaborationInvitation.query.filter(CollaborationInvitation.collaboration_id.in_(collab_ids_subq)).delete(synchronize_session=False)

        # Collaborations
        BookCollaboration.query.filter_by(book_project_id=book_id).delete()
        
        # Analytics
        BookAnalytics.query.filter_by(book_project_id=book_id).delete()
        
        # Notifications
        BookNotification.query.filter_by(book_project_id=book_id).delete()
        
        delete_book_chapter_version_graph_for_project(book_id)
        
    except Exception as e:
        print(f"Error cleaning up book data for book {book_id}: {e}")


def cleanup_book_files(book):
    """Delete all files associated with a book"""
    base_path = os.path.join(os.getcwd(), 'glconnect', 'static')
    
    try:
        # Delete cover image
        if book.cover_image:
            cover_path = os.path.join(base_path, book.cover_image)
            if os.path.exists(cover_path):
                os.remove(cover_path)
        
        # Delete digital book file
        if book.digital_file_path:
            digital_path = os.path.join(base_path, book.digital_file_path)
            if os.path.exists(digital_path):
                os.remove(digital_path)
        
        # Delete audiobook file
        if book.audiobook_file_path:
            audio_path = os.path.join(base_path, book.audiobook_file_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
    except Exception as e:
        print(f"Error deleting files for book {book.id}: {e}")

