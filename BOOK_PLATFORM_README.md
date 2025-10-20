# Book Platform - Complete Documentation

## Overview

The Book Platform is a comprehensive web application that allows users to create, collaborate on, publish, and sell books. It's designed as a separate module that can be easily integrated into your existing Flask application without affecting your current features.

## Features

### Core Features
- **Book Creation & Management**: Create and manage multiple book projects
- **Rich Text Editor**: Full-featured editor with formatting tools
- **Real-time Collaboration**: Multiple users can edit simultaneously
- **Comment System**: Add comments and feedback on specific text sections
- **Version Control**: Track changes and revert to previous versions
- **Publishing**: Publish books to a marketplace
- **Sales System**: Handle book purchases and royalty payments
- **User Profiles**: Author profiles with pen names and bios

### Advanced Features
- **WebSocket Integration**: Real-time updates and collaboration
- **Security**: Input validation, rate limiting, CSRF protection
- **Analytics**: Track book performance and sales
- **Notifications**: Real-time notifications for comments and invitations
- **File Upload**: Secure cover image and file handling
- **Responsive Design**: Works on desktop and mobile devices

## Installation

### 1. Install Dependencies

Add these packages to your `requirements.txt`:

```txt
Flask-SocketIO==5.3.6
ebooklib==0.18
reportlab==4.0.4
bleach==6.0.0
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 2. Integration

Add this to your main Flask application file:

```python
from flask import Flask
from flask_socketio import SocketIO
from glconnect.models import db
from glconnect.book_platform_integration import init_book_platform

def create_app():
    app = Flask(__name__)
    
    # Your existing configuration
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'your-database-uri'
    
    # Initialize existing components
    db.init_app(app)
    
    # Initialize book platform
    app, socketio = init_book_platform(app)
    
    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    socketio.run(app, debug=True)
```

### 3. Database Setup

The book platform will automatically create its own database tables. These are separate from your existing tables and can be easily removed if needed.

To manually create tables:
```python
from glconnect.book_platform_integration import create_book_platform_tables
create_book_platform_tables()
```

To remove all book platform tables:
```python
from glconnect.book_platform_integration import drop_book_platform_tables
drop_book_platform_tables()
```

## Usage

### Accessing the Platform

Once integrated, users can access the book platform at:
- Main dashboard: `/mybook/`
- Create book: `/mybook/books/create`
- Marketplace: `/mybook/marketplace`

### User Workflow

1. **Setup Profile**: First-time users need to create an author profile
2. **Create Book**: Start a new book project with title, description, and genre
3. **Write Chapters**: Use the rich text editor to write content
4. **Collaborate**: Invite editors and reviewers to collaborate
5. **Review & Edit**: Use the comment system for feedback
6. **Publish**: Make the book available in the marketplace
7. **Sell**: Handle purchases and receive royalty payments

## API Endpoints

### Book Management
- `GET /mybook/` - Dashboard
- `GET /mybook/books` - List user's books
- `POST /mybook/books/create` - Create new book
- `GET /mybook/books/<id>` - View book details
- `POST /mybook/books/<id>/edit` - Edit book details
- `POST /mybook/books/<id>/publish` - Publish book

### Chapter Management
- `GET /mybook/books/<id>/chapters` - List chapters
- `POST /mybook/books/<id>/chapters/create` - Create chapter
- `GET /mybook/books/<id>/chapters/<id>` - View chapter
- `POST /mybook/books/<id>/chapters/<id>/edit` - Edit chapter

### Collaboration
- `GET /mybook/books/<id>/collaborate` - Collaboration management
- `POST /mybook/books/<id>/invite` - Invite collaborator
- `GET /mybook/invitations/<uuid>` - Accept invitation

### Comments
- `POST /mybook/books/<id>/chapters/<id>/comments` - Add comment
- `POST /mybook/comments/<id>/resolve` - Resolve comment

### Marketplace
- `GET /mybook/marketplace` - Browse marketplace
- `POST /mybook/books/<id>/purchase` - Purchase book

## Database Schema

The book platform uses separate tables with the prefix `book_`:

### Core Tables
- `book_platform_users` - Extended user profiles
- `book_projects` - Book projects
- `book_chapters` - Individual chapters
- `book_collaborations` - User collaborations
- `book_comments` - Comments and feedback

### Supporting Tables
- `collaboration_invitations` - Invitation system
- `book_versions` - Version control
- `book_purchases` - Purchase records
- `book_sales` - Sales and royalties
- `realtime_sessions` - WebSocket sessions
- `book_analytics` - Performance metrics
- `book_notifications` - User notifications

## Security Features

### Input Validation
- All user inputs are validated and sanitized
- HTML content is cleaned using Bleach
- File uploads are validated for security

### Rate Limiting
- API endpoints are rate-limited
- Configurable limits per user/IP

### CSRF Protection
- All forms include CSRF tokens
- API endpoints validate CSRF tokens

### Content Security Policy
- Strict CSP headers prevent XSS attacks
- Only trusted sources allowed for scripts/styles

## Real-time Features

### WebSocket Events
- `join_book` - Join a book collaboration session
- `leave_book` - Leave a collaboration session
- `content_change` - Broadcast content changes
- `cursor_position` - Share cursor positions
- `add_comment` - Add comments in real-time
- `resolve_comment` - Resolve comments
- `typing` - Show typing indicators

### Collaboration Features
- Multiple users can edit simultaneously
- Real-time cursor sharing
- Live comment system
- Active user indicators

## Customization

### Styling
The platform includes comprehensive CSS in `static/book_platform.css`:
- Responsive design
- Dark mode support
- Print styles
- Custom components

### JavaScript
Rich JavaScript functionality in `static/book_platform.js`:
- Rich text editor
- Real-time collaboration
- Auto-save functionality
- Comment system

### Templates
All templates are in `templates/book_platform/`:
- Dashboard
- Book creation/editing
- Chapter editor
- Collaboration management
- Marketplace

## Configuration

### Environment Variables
```bash
# WebSocket configuration
FLASK_SOCKETIO_CORS_ALLOWED_ORIGINS=*

# Security settings
BOOK_PLATFORM_RATE_LIMIT=100
BOOK_PLATFORM_RATE_WINDOW=3600

# File upload settings
BOOK_PLATFORM_MAX_FILE_SIZE=10485760  # 10MB
BOOK_PLATFORM_ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,webp
```

### Database Configuration
The platform uses your existing database connection. No additional configuration needed.

## Monitoring & Analytics

### Built-in Analytics
- Book views and downloads
- Sales metrics
- User engagement
- Collaboration activity

### Logging
Security events are logged for monitoring:
- User actions
- Failed attempts
- Rate limit violations
- File uploads

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check if Flask-SocketIO is properly installed
   - Verify CORS settings
   - Check firewall/proxy settings

2. **Database Errors**
   - Ensure database tables are created
   - Check foreign key constraints
   - Verify user permissions

3. **File Upload Issues**
   - Check file size limits
   - Verify allowed file types
   - Ensure upload directory permissions

### Debug Mode
Enable debug mode for detailed error messages:
```python
app.config['DEBUG'] = True
```

## Performance Optimization

### Database Optimization
- Indexes on frequently queried columns
- Connection pooling
- Query optimization

### Caching
- Static file caching
- Database query caching
- Session caching

### CDN Integration
- Static assets served via CDN
- Image optimization
- Compression

## Backup & Recovery

### Database Backup
```bash
# Backup book platform tables
pg_dump -t book_* your_database > book_platform_backup.sql
```

### Data Export
Books can be exported in multiple formats:
- EPUB for e-readers
- PDF for printing
- HTML for web display

## Support & Maintenance

### Regular Maintenance
- Clean up old sessions
- Archive resolved comments
- Update analytics data
- Security updates

### Monitoring
- Monitor WebSocket connections
- Track API usage
- Monitor error rates
- Performance metrics

## License

This book platform module is designed to be easily removable from your main application. All code is self-contained and uses separate database tables.

## Contributing

To contribute to the book platform:
1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure security best practices

## Version History

- v1.0.0 - Initial release with core features
- Real-time collaboration
- Marketplace functionality
- Security features
- Analytics and monitoring




