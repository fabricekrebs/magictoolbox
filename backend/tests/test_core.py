"""
Tests for core utilities.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.core.utils import (
    get_file_hash,
    get_file_extension,
    get_mime_type,
    validate_file_size,
    validate_file_type
)


class TestFileUtils:
    """Test file utility functions."""
    
    def test_get_file_extension(self):
        """Test extracting file extension."""
        assert get_file_extension('test.jpg') == '.jpg'
        assert get_file_extension('test.PDF') == '.pdf'
        assert get_file_extension('test') == ''
        assert get_file_extension('test.tar.gz') == '.gz'
    
    def test_get_mime_type(self):
        """Test MIME type detection."""
        assert get_mime_type('test.jpg') == 'image/jpeg'
        assert get_mime_type('test.png') == 'image/png'
        assert get_mime_type('test.pdf') == 'application/pdf'
    
    def test_validate_file_size(self):
        """Test file size validation."""
        small_file = SimpleUploadedFile('test.txt', b'content', content_type='text/plain')
        
        assert validate_file_size(small_file, 1000) is True
        assert validate_file_size(small_file, 5) is False
    
    def test_validate_file_type(self):
        """Test file type validation."""
        assert validate_file_type('test.jpg', ['.jpg', '.png']) is True
        assert validate_file_type('test.PDF', ['.pdf']) is True
        assert validate_file_type('test.exe', ['.jpg', '.png']) is False
    
    def test_get_file_hash(self):
        """Test file hash generation."""
        file = SimpleUploadedFile('test.txt', b'content', content_type='text/plain')
        
        hash1 = get_file_hash(file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 produces 64 hex characters
        
        # Same content should produce same hash
        file.seek(0)
        hash2 = get_file_hash(file)
        assert hash1 == hash2
