# Cascade Delete Setup for User/Author Deletion

## Summary

This document describes the cascade delete behavior implemented to ensure that when an author/user is removed from the database, all their books and associated data are automatically deleted.

## Changes Made

### 1. Database Model Updates

#### `glconnect/book_platform_models.py`
- Added `ondelete='CASCADE'` to `BookPlatformUser.user_id` foreign key
  - When a User is deleted, their BookPlatformUser profile is automatically deleted
- Added `ondelete='CASCADE'` to `BookProject.author_id` foreign key
  - When a BookPlatformUser is deleted, all their authored books are automatically deleted
- Added `cascade='all, delete-orphan'` to `BookPlatformUser.authored_books` relationship
  - Ensures proper cleanup of books when author is deleted

#### `glconnect/models.py`
- Added `ondelete='CASCADE'` to `Writer.user_id` foreign key
  - When a User is deleted, their Writer profile is automatically deleted
- Added `ondelete='CASCADE'` to `Book.writer_id` foreign key
  - When a Writer is deleted, all their books are automatically deleted
- Added `cascade='all, delete-orphan'` to `Writer.books` relationship
  - Ensures proper cleanup of books when writer is deleted

### 2. Author Information Updates

Author information (name, username, pen_name) is displayed using SQLAlchemy relationships:
- Templates use: `book.author.pen_name or book.author.user.username`
- Since relationships are lazy-loaded, any updates to User or BookPlatformUser information are **automatically reflected** in book displays
- No caching or stale data issues - information is always current

### 3. Utility Functions

Created `glconnect/user_deletion_handler.py` with:
- `delete_user_and_all_data(user_id)` - Safely deletes a user and all associated data
- `cleanup_book_data(book_id)` - Cleans up all data associated with a book
- `cleanup_book_files(book)` - Deletes all files associated with a book

## Database Migration Required

**IMPORTANT:** These changes require updating the database schema to apply the CASCADE constraints.

### Option 1: Using Flask-Migrate (Recommended)
```bash
flask db migrate -m "Add cascade delete to user relationships"
flask db upgrade
```

### Option 2: Manual SQL (if migrations not set up)
```sql
-- For PostgreSQL
ALTER TABLE book_platform_users 
DROP CONSTRAINT book_platform_users_user_id_fkey,
ADD CONSTRAINT book_platform_users_user_id_fkey 
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE book_projects
DROP CONSTRAINT book_projects_author_id_fkey,
ADD CONSTRAINT book_projects_author_id_fkey
FOREIGN KEY (author_id) REFERENCES book_platform_users(id) ON DELETE CASCADE;

ALTER TABLE writers
DROP CONSTRAINT writers_user_id_fkey,
ADD CONSTRAINT writers_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE books
DROP CONSTRAINT books_writer_id_fkey,
ADD CONSTRAINT books_writer_id_fkey
FOREIGN KEY (writer_id) REFERENCES writers(writer_id) ON DELETE CASCADE;
```

## Behavior After Migration

### When User is Deleted:
1. ✅ BookPlatformUser profile deleted (CASCADE)
2. ✅ All authored BookProject records deleted (CASCADE)
3. ✅ All associated chapters, comments, collaborations deleted
4. ✅ Writer profile deleted (CASCADE)
5. ✅ All Writer books deleted (CASCADE)

### When Author Info is Updated:
- ✅ User.username changes → immediately reflected in book displays
- ✅ User.first_name/last_name changes → immediately reflected via relationships
- ✅ BookPlatformUser.pen_name changes → immediately reflected in book displays
- ✅ All templates use `book.author.pen_name or book.author.user.username` pattern

## Testing

To test cascade delete:
1. Create a test user with books
2. Delete the user directly from database: `DELETE FROM users WHERE user_id = X;`
3. Verify all related records are automatically deleted

To test author info updates:
1. Update user username: `UPDATE users SET username = 'newname' WHERE user_id = X;`
2. View any book authored by this user - username should update immediately

## Notes

- Cascade deletes work at the database level, so they're enforced even if someone directly deletes from the database
- Files (cover images, profile pictures) are cleaned up by the utility functions, not by CASCADE (filesystem operations)
- Purchase/Sale records may be kept for business/legal reasons - adjust `user_deletion_handler.py` if needed

