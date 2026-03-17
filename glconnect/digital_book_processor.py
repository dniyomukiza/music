"""
Digital Book Processor - Handles text extraction from various document formats
Supports PDF, EPUB, DOCX, DOC, and TXT files for audio book generation
"""

import os
import tempfile
from typing import Optional, Dict, Any
import logging

# Document processing libraries
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import ebooklib
    from ebooklib import epub
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import textract
    TEXTTRACT_AVAILABLE = False  # Disabled due to dependency conflicts
except ImportError:
    TEXTTRACT_AVAILABLE = False

logger = logging.getLogger(__name__)

class DigitalBookProcessor:
    """Processes digital book files and extracts text for audio generation"""
    
    def __init__(self):
        self.supported_formats = {
            'pdf': self._extract_from_pdf,
            'epub': self._extract_from_epub,
            'docx': self._extract_from_docx,
            'doc': self._extract_from_doc,
            'txt': self._extract_from_txt
        }
    
    def extract_text(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """
        Extract text from a digital book file
        
        Args:
            file_path: Path to the uploaded file
            file_type: File extension (pdf, epub, docx, doc, txt)
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            if file_type.lower() not in self.supported_formats:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            extractor = self.supported_formats[file_type.lower()]
            result = extractor(file_path)
            
            # Clean and validate extracted text
            if result['text']:
                result['text'] = self._clean_text(result['text'])
                result['word_count'] = len(result['text'].split())
                result['success'] = True
            else:
                result['success'] = False
                result['error'] = "No text content found in file"
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'word_count': 0,
                'metadata': {}
            }
    
    def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PDF file"""
        if not PDF_AVAILABLE:
            raise ImportError("PyPDF2 is required for PDF processing")
        
        text = ""
        metadata = {}
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                if pdf_reader.metadata:
                    metadata = {
                        'title': pdf_reader.metadata.get('/Title', ''),
                        'author': pdf_reader.metadata.get('/Author', ''),
                        'subject': pdf_reader.metadata.get('/Subject', ''),
                        'creator': pdf_reader.metadata.get('/Creator', ''),
                        'producer': pdf_reader.metadata.get('/Producer', ''),
                        'creation_date': str(pdf_reader.metadata.get('/CreationDate', '')),
                        'modification_date': str(pdf_reader.metadata.get('/ModDate', ''))
                    }
                
                # Extract text from all pages
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
        except Exception as e:
            logger.error(f"Error reading PDF {file_path}: {str(e)}")
            raise
        
        return {
            'text': text,
            'metadata': metadata,
            'pages': len(pdf_reader.pages) if 'pdf_reader' in locals() else 0
        }
    
    def _extract_from_epub(self, file_path: str) -> Dict[str, Any]:
        """Extract text from EPUB file"""
        if not EPUB_AVAILABLE:
            raise ImportError("ebooklib is required for EPUB processing")
        
        text = ""
        metadata = {}
        
        try:
            book = epub.read_epub(file_path)
            
            # Extract metadata
            metadata = {
                'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else '',
                'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else '',
                'language': book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else '',
                'publisher': book.get_metadata('DC', 'publisher')[0][0] if book.get_metadata('DC', 'publisher') else '',
                'date': book.get_metadata('DC', 'date')[0][0] if book.get_metadata('DC', 'date') else ''
            }
            
            # Extract text from all items
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content().decode('utf-8')
                    # Basic HTML tag removal
                    import re
                    clean_content = re.sub(r'<[^>]+>', '', content)
                    text += clean_content + "\n"
                    
        except Exception as e:
            logger.error(f"Error reading EPUB {file_path}: {str(e)}")
            raise
        
        return {
            'text': text,
            'metadata': metadata
        }
    
    def _extract_from_docx(self, file_path: str) -> Dict[str, Any]:
        """Extract text from DOCX file"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx is required for DOCX processing")
        
        text = ""
        metadata = {}
        
        try:
            doc = Document(file_path)
            
            # Extract metadata
            metadata = {
                'title': doc.core_properties.title or '',
                'author': doc.core_properties.author or '',
                'subject': doc.core_properties.subject or '',
                'keywords': doc.core_properties.keywords or '',
                'created': str(doc.core_properties.created) if doc.core_properties.created else '',
                'modified': str(doc.core_properties.modified) if doc.core_properties.modified else ''
            }
            
            # Extract text from all paragraphs
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
                
        except Exception as e:
            logger.error(f"Error reading DOCX {file_path}: {str(e)}")
            raise
        
        return {
            'text': text,
            'metadata': metadata
        }
    
    def _extract_from_doc(self, file_path: str) -> Dict[str, Any]:
        """Extract text from DOC file - currently not supported due to dependency conflicts"""
        return {
            'success': False,
            'error': 'DOC file processing is temporarily unavailable due to dependency conflicts. Please convert your DOC file to DOCX format.',
            'text': '',
            'metadata': {}
        }
    
    def _extract_from_txt(self, file_path: str) -> Dict[str, Any]:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
            
            return {
                'text': text,
                'metadata': {}
            }
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    text = file.read()
                return {
                    'text': text,
                    'metadata': {}
                }
            except Exception as e:
                logger.error(f"Error reading TXT {file_path}: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error reading TXT {file_path}: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers (basic patterns)
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^Page \d+$', '', text, flags=re.MULTILINE)
        
        # Remove excessive line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic file information"""
        try:
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'exists': True
            }
        except OSError:
            return {
                'size': 0,
                'modified': 0,
                'exists': False
            }

# Global processor instance
digital_book_processor = DigitalBookProcessor()
