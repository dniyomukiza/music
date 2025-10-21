# Book Platform Integration Guide

## Quick Start

Follow these steps to integrate the book platform into your existing Flask application:

### 1. Install Dependencies

Add these to your `requirements.txt`:
```
Flask-SocketIO==5.3.6
ebooklib==0.18
reportlab==4.0.4
bleach==6.0.0
```

Install them:
```bash
pip install -r requirements.txt
```

### 2. Update Your Main App File

In your main Flask application file (e.g., `run.py` or `app.py`), add:

```python
from flask_socketio import SocketIO
from glconnect.book_platform_integration import init_book_platform

# After your existing app setup
app, socketio = init_book_platform(app)

# Change your app.run() to:
if __name__ == '__main__':
    socketio.run(app, debug=True)
```

### 3. Test the Integration

Run the test script:
```bash
python test_book_platform.py
```

### 4. Access the Platform

Once running, users can access:
- Dashboard: `http://your-domain/mybook/`
- Marketplace: `http://your-domain/mybook/marketplace`

## What's Included

### Files Created
- `glconnect/book_platform_models.py` - Database models
- `glconnect/book_platform_routes.py` - Flask routes
- `glconnect/book_platform_websocket.py` - WebSocket handlers
- `glconnect/book_platform_security.py` - Security features
- `glconnect/book_platform_integration.py` - Integration module
- `glconnect/static/book_platform.css` - Styling
- `glconnect/static/book_platform.js` - JavaScript
- `glconnect/templates/book_platform/` - HTML templates
- `test_book_platform.py` - Test script
- `BOOK_PLATFORM_README.md` - Full documentation

### Database Tables
The platform creates separate tables with `book_` prefix:
- `book_platform_users`
- `book_projects`
- `book_chapters`
- `book_collaborations`
- `collaboration_invitations`
- `book_comments`
- `book_versions`
- `chapter_versions`
- `book_purchases`
- `book_sales`
- `realtime_sessions`
- `book_analytics`
- `book_notifications`

## Features Available

### For Authors
- Create and manage book projects
- Write chapters with rich text editor
- Invite collaborators (editors, reviewers)
- Publish books to marketplace
- Track sales and analytics

### For Collaborators
- Accept collaboration invitations
- Edit books in real-time
- Add comments and feedback
- View version history

### For Readers
- Browse marketplace
- Purchase books
- Download free books
- Rate and review books

### Real-time Features
- Live editing with multiple users
- Real-time comments
- Typing indicators
- Active user display

## Security Features

- Input validation and sanitization
- Rate limiting on API endpoints
- CSRF protection
- Secure file uploads
- Content Security Policy headers
- SQL injection prevention

## Customization

### Styling
Edit `glconnect/static/book_platform.css` to customize:
- Colors and themes
- Layout and spacing
- Responsive breakpoints
- Dark mode support

### Functionality
Modify the route handlers in `glconnect/book_platform_routes.py` to:
- Add new features
- Change business logic
- Integrate with external services

### Templates
Update HTML templates in `glconnect/templates/book_platform/` to:
- Modify the user interface
- Add new pages
- Change the layout

## Removing the Platform

If you need to remove the book platform:

### 1. Remove Integration Code
Remove the integration code from your main app file.

### 2. Drop Database Tables
```python
from glconnect.book_platform_integration import drop_book_platform_tables
drop_book_platform_tables()
```

### 3. Remove Files
Delete all the book platform files listed above.

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Make sure all dependencies are installed
   - Check Python path and module structure

2. **Database Errors**
   - Verify database connection
   - Check table creation permissions

3. **WebSocket Issues**
   - Ensure Flask-SocketIO is installed
   - Check CORS settings
   - Verify proxy/firewall configuration

4. **Static File Issues**
   - Check file permissions
   - Verify static file serving configuration

### Getting Help

1. Run the test script to identify issues
2. Check the full documentation in `BOOK_PLATFORM_README.md`
3. Review error logs for specific error messages
4. Ensure all dependencies are properly installed

## Next Steps

After successful integration:

1. **Configure Settings**: Set up environment variables for production
2. **Customize Styling**: Modify CSS to match your brand
3. **Add Features**: Extend functionality as needed
4. **Set Up Monitoring**: Configure logging and analytics
5. **Deploy**: Follow your standard deployment process

The book platform is now ready to use! Users can start creating books, collaborating, and selling their work through your platform.





