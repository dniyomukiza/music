# Digital Book Upload & Audio Generation Feature - Ink Studio

## Overview

This feature allows writers to upload existing digital books (PDF, EPUB, DOCX, TXT) and automatically generate audiobook versions using Google Cloud Text-to-Speech. Both digital and audio versions can be sold separately or as bundles in the marketplace through Ink Studio.

## Features Added

### ✅ Digital Book Upload
- Support for multiple file formats: PDF, EPUB, DOCX, TXT
- Automatic text extraction from uploaded documents
- File validation and security checks
- Cover image upload support

### ✅ Audio Book Generation
- Automatic conversion of extracted text to audio
- Multiple voice options (English US/UK, Male/Female)
- Background processing with progress tracking
- High-quality MP3 output

### ✅ Dual Format Sales
- Separate pricing for digital and audio versions
- Bundle pricing with discounts
- Secure download system for purchased content
- Author royalty tracking (70% to author, 30% platform fee)

### ✅ Enhanced Database Models
- Extended `BookProject` model with digital file support
- Audio generation task tracking
- File metadata storage

## Installation & Setup

### 1. Install Required Dependencies

```bash
pip install -r requirements.txt
```

New dependencies added:
- `PyPDF2==3.0.1` - PDF text extraction
- `python-docx==1.1.0` - DOCX processing (already existed)
- `ebooklib==0.18` - EPUB processing (already existed)

### 2. Database Migration

The new database fields will be automatically created when you run the application. If you need to manually create them:

```python
from glconnect.book_platform_models import db
db.create_all()
```

### 3. Directory Setup

Create the required directories for file storage:

```bash
mkdir -p glconnect/static/digital_books
mkdir -p glconnect/static/book_covers
mkdir -p glconnect/static/audio/audiobooks
```

### 4. Google Cloud TTS Setup

Ensure your Google Cloud Text-to-Speech credentials are properly configured (already set up for news broadcasts).

## Usage Guide

### For Writers

#### Uploading a Digital Book

1. **Access Upload Form**
   - Go to Book Platform Dashboard
   - Click "Upload Digital Book" button
   - Or navigate to `/mybook/upload-digital-book`

2. **Fill Book Information**
   - Enter book title, description, and genre
   - Upload your digital book file (PDF, EPUB, DOCX, DOC, or TXT)
   - Optionally upload a cover image

3. **Set Pricing**
   - Set price for digital version (leave empty for free)
   - Choose whether to generate audiobook
   - Set audiobook price and select voice

4. **Submit & Process**
   - Click "Upload Digital Book"
   - System extracts text and creates book project
   - Audiobook generation starts in background (if requested)

#### Monitoring Audio Generation

- Check audio generation status at `/mybook/books/{book_id}/audio-generation-status`
- Progress updates: pending → processing → completed/failed
- Receive notifications when generation completes

### For Readers

#### Purchasing Books

1. **Browse Marketplace**
   - Visit `/mybook/marketplace`
   - Books show both digital and audio availability

2. **Purchase Options**
   - **Digital Only**: Buy just the digital book
   - **Audio Only**: Buy just the audiobook
   - **Bundle**: Buy both with 20% discount

3. **Download Content**
   - Access purchased content from your library
   - Download digital files or audio files
   - Files are served securely with purchase verification

## API Endpoints

### New Routes Added

```
POST /mybook/upload-digital-book
GET  /mybook/books/{id}/audio-generation-status
GET  /mybook/books/{id}/download-digital
GET  /mybook/books/{id}/download-audio
```

### Request/Response Examples

#### Upload Digital Book
```json
POST /mybook/upload-digital-book
Content-Type: multipart/form-data

{
  "title": "My Book Title",
  "description": "Book description",
  "genre": "Fiction",
  "digital_book_file": "<file>",
  "cover_image": "<file>",
  "digital_price": 9.99,
  "generate_audiobook": true,
  "audiobook_price": 14.99,
  "audiobook_voice": "en-US-Standard-A"
}
```

#### Audio Generation Status
```json
GET /mybook/books/123/audio-generation-status

Response:
{
  "status": "processing",
  "progress": 45,
  "error_message": null,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": null
}
```

## File Processing Details

### Supported Formats

| Format | Library | Notes |
|--------|---------|-------|
| PDF | PyPDF2 | Extracts text and metadata |
| EPUB | ebooklib | Handles HTML content extraction |
| DOCX | python-docx | Native Word document support |
| TXT | Built-in | Plain text files |
| DOC | Not supported | Temporarily unavailable due to dependency conflicts |

### Text Extraction Process

1. **File Validation**: Check file type and size (max 50MB)
2. **Text Extraction**: Use appropriate library for file format
3. **Text Cleaning**: Remove excessive whitespace, page numbers
4. **Metadata Extraction**: Extract title, author, creation date
5. **Word Count**: Calculate total word count for pricing

### Audio Generation Process

1. **Text Chunking**: Split text into 5000-character chunks
2. **TTS Processing**: Convert each chunk to audio using Google Cloud TTS
3. **Audio Combination**: Use FFmpeg to combine chunks into final audiobook
4. **Quality Settings**: 128kbps MP3, 44.1kHz sample rate, stereo
5. **Cleanup**: Remove temporary chunk files

## Security Features

### File Upload Security
- File type validation (whitelist approach)
- File size limits (50MB max)
- Secure filename generation with UUIDs
- Path traversal protection

### Download Security
- Purchase verification before download
- Author access control
- Secure file serving with proper headers
- No direct file system access

### Content Protection
- Files stored outside web root
- Access control based on purchase records
- Audit trail for all downloads

## Performance Considerations

### File Processing
- Background processing for audio generation
- Chunked text processing to handle large books
- Progress tracking for long operations
- Error handling and retry logic

### Storage Optimization
- Compressed audio files (128kbps MP3)
- Efficient file organization
- Cleanup of temporary files
- CDN-ready file structure

### Database Optimization
- Indexed foreign keys
- Efficient query patterns
- Minimal data duplication

## Troubleshooting

### Common Issues

#### File Upload Fails
- Check file size (must be < 50MB)
- Verify file format is supported
- Ensure proper permissions on upload directories

#### Text Extraction Fails
- Verify file is not corrupted
- Check if file is password-protected (PDFs)
- Ensure sufficient disk space

#### Audio Generation Fails
- Verify Google Cloud TTS credentials
- Check FFmpeg installation
- Ensure sufficient disk space for audio files
- Check TTS quota limits

#### Download Issues
- Verify user has purchased the book
- Check file exists on disk
- Ensure proper file permissions

### Debug Mode

Enable debug logging for detailed error information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features
- Batch upload for multiple books
- Custom voice training
- Audio preview generation
- Advanced pricing models
- Analytics for audio vs digital sales
- Mobile app integration

### Integration Opportunities
- DRM protection for premium content
- Subscription-based access
- Social sharing features
- Review and rating system
- Author collaboration tools

## Support

For technical support or feature requests:
- Check the troubleshooting section above
- Review error logs for specific issues
- Contact the development team for advanced issues

## License

This feature is part of the existing book platform and follows the same licensing terms.
