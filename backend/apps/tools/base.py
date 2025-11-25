"""
Base tool interface for plugin system.

All tool plugins must inherit from BaseTool and implement required methods.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from django.core.files.uploadedfile import UploadedFile
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """
    Abstract base class for all conversion tools.
    
    Tool plugins must inherit from this class and implement:
    - validate(): Validate input parameters
    - process(): Execute tool logic
    - cleanup(): Clean up temporary resources
    """
    
    # Tool metadata (override in subclass)
    name: str = ""
    display_name: str = ""
    description: str = ""
    category: str = ""
    version: str = "1.0.0"
    icon: str = "box"  # Bootstrap icon name
    
    # File constraints (override in subclass)
    allowed_input_types: List[str] = []  # e.g., ['.jpg', '.png']
    max_file_size: int = 50 * 1024 * 1024  # 50MB default
    
    def __init__(self):
        """Initialize tool with logger."""
        self.logger = logger.getChild(self.name)
    
    @abstractmethod
    def validate(
        self,
        input_file: UploadedFile,
        parameters: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate input file and parameters.
        
        Args:
            input_file: Uploaded file to process
            parameters: Tool-specific parameters
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def process(
        self,
        input_file: UploadedFile,
        parameters: Dict[str, Any]
    ) -> tuple[Any, str]:
        """
        Execute tool processing logic.
        
        Args:
            input_file: Uploaded file to process
            parameters: Tool-specific parameters
        
        Returns:
            Tuple of (output_file_path, output_filename)
        
        Raises:
            Exception: If processing fails
        """
        pass
    
    @abstractmethod
    def cleanup(self, *file_paths: str) -> None:
        """
        Clean up temporary files and resources.
        
        Args:
            *file_paths: Paths to temporary files to remove
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get tool metadata for API discovery.
        
        Returns:
            Dictionary with tool information
        """
        return {
            'name': self.name,
            'slug': self.name,
            'displayName': self.display_name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
            'version': self.version,
            'icon': self.icon,
            'allowedInputTypes': self.allowed_input_types,
            'allowed_input_types': self.allowed_input_types,
            'maxFileSize': self.max_file_size,
            'max_file_size': f"{self.max_file_size / (1024*1024):.0f}MB",
            'supported_formats': self.allowed_input_types,
        }
    
    def validate_file_type(self, filename: str) -> bool:
        """
        Check if file type is allowed.
        
        Args:
            filename: Name of file to check
        
        Returns:
            True if file type is allowed
        """
        from pathlib import Path
        extension = Path(filename).suffix.lower()
        return extension in self.allowed_input_types
    
    def validate_file_size(self, file: UploadedFile) -> bool:
        """
        Check if file size is within limits.
        
        Args:
            file: Uploaded file to check
        
        Returns:
            True if file size is allowed
        """
        return file.size <= self.max_file_size
