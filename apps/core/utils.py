"""
Utility functions for MagicToolbox core app.
"""
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional
from django.core.files.uploadedfile import UploadedFile


def get_file_hash(file: UploadedFile, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of uploaded file.
    
    Args:
        file: Django UploadedFile instance
        algorithm: Hash algorithm to use (sha256, md5, etc.)
    
    Returns:
        Hexadecimal hash string
    """
    hasher = hashlib.new(algorithm)
    
    # Reset file pointer
    file.seek(0)
    
    # Read and hash in chunks
    for chunk in file.chunks():
        hasher.update(chunk)
    
    # Reset file pointer
    file.seek(0)
    
    return hasher.hexdigest()


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.
    
    Args:
        filename: Name of the file
    
    Returns:
        File extension with dot (e.g., '.jpg') or empty string
    """
    return Path(filename).suffix.lower()


def get_mime_type(filename: str) -> Optional[str]:
    """
    Guess MIME type from filename.
    
    Args:
        filename: Name of the file
    
    Returns:
        MIME type string or None
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type


def validate_file_size(file: UploadedFile, max_size: int) -> bool:
    """
    Validate that file size doesn't exceed maximum.
    
    Args:
        file: Django UploadedFile instance
        max_size: Maximum allowed size in bytes
    
    Returns:
        True if valid, False otherwise
    """
    return file.size <= max_size


def validate_file_type(filename: str, allowed_types: list[str]) -> bool:
    """
    Validate that file extension is in allowed list.
    
    Args:
        filename: Name of the file
        allowed_types: List of allowed extensions (e.g., ['.jpg', '.png'])
    
    Returns:
        True if valid, False otherwise
    """
    extension = get_file_extension(filename)
    return extension in [ext.lower() for ext in allowed_types]
