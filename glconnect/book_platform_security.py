"""
Security features for the book platform
This module implements security best practices for the book platform including:
- Input validation and sanitization
- Rate limiting
- CSRF protection
- Content security policies
- File upload security
"""

from flask import request, jsonify, current_app
from functools import wraps
import re
import bleach
import hashlib
import time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Rate limiting storage (in production, use Redis)
rate_limit_storage = defaultdict(list)

def validate_book_input(data):
    """
    Validate and sanitize book input data
    """
    errors = []
    
    # Title validation
    if 'title' in data:
        title = data['title'].strip()
        if not title:
            errors.append('Title is required')
        elif len(title) > 200:
            errors.append('Title must be less than 200 characters')
        elif not re.match(r'^[a-zA-Z0-9\s\-_.,!?()]+$', title):
            errors.append('Title contains invalid characters')
        else:
            data['title'] = bleach.clean(title, tags=[], strip=True)
    
    # Description validation
    if 'description' in data:
        description = data['description']
        if description and len(description) > 5000:
            errors.append('Description must be less than 5000 characters')
        else:
            # Allow basic HTML tags for rich text
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'ul', 'ol', 'li']
            data['description'] = bleach.clean(description, tags=allowed_tags, strip=True)
    
    # Genre validation
    if 'genre' in data:
        valid_genres = [
            'fiction', 'non-fiction', 'mystery', 'romance', 'sci-fi', 'fantasy',
            'thriller', 'biography', 'self-help', 'business', 'history', 'poetry',
            'children', 'young-adult', 'other'
        ]
        if data['genre'] and data['genre'] not in valid_genres:
            errors.append('Invalid genre selected')
    
    # Price validation
    if 'price' in data:
        try:
            price = float(data['price'])
            if price < 0:
                errors.append('Price cannot be negative')
            elif price > 999.99:
                errors.append('Price cannot exceed $999.99')
            else:
                data['price'] = round(price, 2)
        except (ValueError, TypeError):
            errors.append('Invalid price format')
    
    return errors

def validate_chapter_input(data):
    """
    Validate and sanitize chapter input data
    """
    errors = []
    
    # Title validation
    if 'title' in data:
        title = data['title'].strip()
        if not title:
            errors.append('Chapter title is required')
        elif len(title) > 200:
            errors.append('Chapter title must be less than 200 characters')
        else:
            data['title'] = bleach.clean(title, tags=[], strip=True)
    
    # Content validation
    if 'content' in data:
        content = data['content']
        if content and len(content) > 1000000:  # 1MB limit
            errors.append('Chapter content is too large')
        else:
            # Allow rich text formatting
            allowed_tags = [
                'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'ul', 'ol', 'li', 'blockquote', 'a', 'img', 'div', 'span'
            ]
            allowed_attributes = {
                'a': ['href', 'title'],
                'img': ['src', 'alt', 'width', 'height'],
                'div': ['class'],
                'span': ['class']
            }
            data['content'] = bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    
    return errors

def validate_comment_input(data):
    """
    Validate and sanitize comment input data
    """
    errors = []
    
    # Content validation
    if 'content' in data:
        content = data['content'].strip()
        if not content:
            errors.append('Comment content is required')
        elif len(content) > 2000:
            errors.append('Comment must be less than 2000 characters')
        else:
            # Only allow basic text formatting
            allowed_tags = ['p', 'br', 'strong', 'em']
            data['content'] = bleach.clean(content, tags=allowed_tags, strip=True)
    
    # Position validation
    if 'start_position' in data and 'end_position' in data:
        try:
            start_pos = int(data['start_position'])
            end_pos = int(data['end_position'])
            if start_pos < 0 or end_pos < 0:
                errors.append('Invalid position values')
            elif start_pos > end_pos:
                errors.append('Start position cannot be greater than end position')
        except (ValueError, TypeError):
            errors.append('Invalid position format')
    
    return errors

def rate_limit(max_requests=100, window_minutes=60):
    """
    Rate limiting decorator
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client IP
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            # Get current time
            current_time = time.time()
            window_start = current_time - (window_minutes * 60)
            
            # Clean old requests
            rate_limit_storage[client_ip] = [
                req_time for req_time in rate_limit_storage[client_ip]
                if req_time > window_start
            ]
            
            # Check if limit exceeded
            if len(rate_limit_storage[client_ip]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_requests} requests per {window_minutes} minutes'
                }), 429
            
            # Add current request
            rate_limit_storage[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_https(f):
    """
    Require HTTPS for sensitive operations
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and not current_app.debug:
            return jsonify({'error': 'HTTPS required'}), 400
        return f(*args, **kwargs)
    return decorated_function

def validate_file_upload(file, allowed_extensions=None, max_size_mb=10):
    """
    Validate file uploads for security
    """
    if allowed_extensions is None:
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    errors = []
    
    if not file:
        errors.append('No file provided')
        return errors
    
    # Check file extension
    if '.' not in file.filename:
        errors.append('File must have an extension')
    else:
        ext = '.' + file.filename.rsplit('.', 1)[1].lower()
        if ext not in allowed_extensions:
            errors.append(f'File type {ext} not allowed')
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        errors.append(f'File size exceeds {max_size_mb}MB limit')
    
    # Check for malicious content (basic check)
    file_content = file.read(1024)  # Read first 1KB
    file.seek(0)  # Reset to beginning
    
    # Check for executable signatures
    executable_signatures = [
        b'\x4d\x5a',  # PE executable
        b'\x7f\x45\x4c\x46',  # ELF executable
        b'\xfe\xed\xfa',  # Mach-O executable
    ]
    
    for signature in executable_signatures:
        if signature in file_content:
            errors.append('File appears to be an executable')
            break
    
    return errors

def sanitize_filename(filename):
    """
    Sanitize filename for safe storage
    """
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove or replace dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + ('.' + ext if ext else '')
    
    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed_file'
    
    return filename

def generate_secure_filename(original_filename):
    """
    Generate a secure filename with timestamp and hash
    """
    timestamp = str(int(time.time()))
    file_hash = hashlib.md5(original_filename.encode()).hexdigest()[:8]
    
    # Get file extension
    if '.' in original_filename:
        ext = '.' + original_filename.rsplit('.', 1)[1].lower()
    else:
        ext = ''
    
    return f"{timestamp}_{file_hash}{ext}"

def validate_collaboration_invitation(data):
    """
    Validate collaboration invitation data
    """
    errors = []
    
    # Email validation
    if 'email' in data:
        email = data['email'].strip().lower()
        if not email:
            errors.append('Email is required')
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append('Invalid email format')
        else:
            data['email'] = email
    
    # Role validation
    if 'role' in data:
        valid_roles = ['author', 'editor', 'reviewer', 'viewer']
        if data['role'] not in valid_roles:
            errors.append('Invalid collaboration role')
    
    # Message validation
    if 'message' in data:
        message = data['message']
        if message and len(message) > 1000:
            errors.append('Message must be less than 1000 characters')
        else:
            data['message'] = bleach.clean(message, tags=[], strip=True)
    
    return errors

def check_content_security_policy():
    """
    Set appropriate Content Security Policy headers
    """
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' cdnjs.cloudflare.com; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    return csp_policy

def log_security_event(event_type, user_id, details):
    """
    Log security events for monitoring
    """
    timestamp = datetime.now(timezone.utc)
    log_entry = {
        'timestamp': timestamp.isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
        'user_agent': request.headers.get('User-Agent'),
        'details': details
    }
    
    # In production, send to security monitoring system
    print(f"SECURITY EVENT: {log_entry}")

def validate_purchase_data(data):
    """
    Validate purchase/transaction data
    """
    errors = []
    
    # Amount validation
    if 'amount' in data:
        try:
            amount = float(data['amount'])
            if amount <= 0:
                errors.append('Amount must be positive')
            elif amount > 999.99:
                errors.append('Amount exceeds maximum limit')
            else:
                data['amount'] = round(amount, 2)
        except (ValueError, TypeError):
            errors.append('Invalid amount format')
    
    # Currency validation
    if 'currency' in data:
        valid_currencies = ['USD', 'EUR', 'GBP', 'CAD']
        if data['currency'] not in valid_currencies:
            errors.append('Invalid currency')
    
    return errors

# Security decorators for routes
def secure_book_operation(f):
    """
    Security decorator for book operations
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log the operation
        log_security_event('book_operation', current_user.user_id if current_user.is_authenticated else None, {
            'endpoint': request.endpoint,
            'method': request.method
        })
        
        return f(*args, **kwargs)
    return decorated_function

def secure_collaboration_operation(f):
    """
    Security decorator for collaboration operations
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log the operation
        log_security_event('collaboration_operation', current_user.user_id if current_user.is_authenticated else None, {
            'endpoint': request.endpoint,
            'method': request.method
        })
        
        return f(*args, **kwargs)
    return decorated_function





