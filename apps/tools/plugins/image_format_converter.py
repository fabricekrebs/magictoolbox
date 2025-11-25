"""
Example image format converter tool.

This is a sample tool demonstrating the plugin system.
Converts images between different formats (e.g., PNG to JPG, WEBP to PNG).
"""
from typing import Any, Dict, Optional, Tuple
from django.core.files.uploadedfile import UploadedFile
from apps.tools.base import BaseTool
from apps.core.exceptions import ToolValidationError, ToolExecutionError
from pathlib import Path
import tempfile
import os

try:
    from PIL import Image
except ImportError:
    Image = None


class ImageFormatConverter(BaseTool):
    """
    Convert images between different formats.
    
    Supports: JPG, PNG, WEBP, BMP, GIF, TIFF, ICO, TGA, PPM, PGM, PBM
    """
    
    # Tool metadata
    name = "image-format-converter"
    display_name = "Image Format Converter"
    description = "Convert images between all common formats (JPG, PNG, WEBP, BMP, GIF, TIFF, ICO, and more)"
    category = "image"
    version = "2.0.0"
    icon = "image"
    
    # File constraints
    allowed_input_types = [
        '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', 
        '.tiff', '.tif', '.ico', '.tga', '.ppm', '.pgm', '.pbm',
        '.pcx', '.sgi', '.im', '.msp', '.dib', '.xbm', '.eps',
        '.heic', '.heif'  # Apple's HEIC/HEIF format
    ]
    max_file_size = 50 * 1024 * 1024  # 50MB per file
    
    # Supported output formats with descriptions
    SUPPORTED_FORMATS = {
        'jpg': {'format': 'JPEG', 'name': 'JPEG', 'description': 'Best for photos, lossy compression'},
        'jpeg': {'format': 'JPEG', 'name': 'JPEG', 'description': 'Best for photos, lossy compression'},
        'png': {'format': 'PNG', 'name': 'PNG', 'description': 'Lossless, supports transparency'},
        'webp': {'format': 'WEBP', 'name': 'WebP', 'description': 'Modern format, great compression'},
        'bmp': {'format': 'BMP', 'name': 'BMP', 'description': 'Uncompressed, large file size'},
        'gif': {'format': 'GIF', 'name': 'GIF', 'description': 'Supports animation, limited colors'},
        'tiff': {'format': 'TIFF', 'name': 'TIFF', 'description': 'High quality, large files'},
        'tif': {'format': 'TIFF', 'name': 'TIFF', 'description': 'High quality, large files'},
        'ico': {'format': 'ICO', 'name': 'ICO', 'description': 'Icon format, multiple sizes'},
        'tga': {'format': 'TGA', 'name': 'TGA', 'description': 'Targa format'},
        'ppm': {'format': 'PPM', 'name': 'PPM', 'description': 'Portable Pixmap'},
        'pgm': {'format': 'PGM', 'name': 'PGM', 'description': 'Portable Graymap'},
        'pbm': {'format': 'PBM', 'name': 'PBM', 'description': 'Portable Bitmap'},
        'heic': {'format': 'HEIC', 'name': 'HEIC', 'description': 'Apple High Efficiency Image'},
        'heif': {'format': 'HEIF', 'name': 'HEIF', 'description': 'High Efficiency Image Format'},
    }
    
    def validate(
        self,
        input_file: UploadedFile,
        parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and parameters.
        
        Required parameters:
        - output_format: Target format (jpg, png, webp, bmp, gif)
        
        Optional parameters:
        - quality: JPEG quality 1-100 (default 85)
        """
        # Check Pillow is installed
        if Image is None:
            return False, "Pillow library not installed"
        
        # Validate file type
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"
        
        # Validate file size
        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"
        
        # Validate output format parameter
        output_format = parameters.get('output_format', '').lower()
        if not output_format:
            return False, "Missing required parameter: output_format"
        
        if output_format not in self.SUPPORTED_FORMATS:
            return False, f"Unsupported output format: {output_format}. Supported: {', '.join(self.SUPPORTED_FORMATS.keys())}"
        
        # Validate quality parameter (if provided)
        quality = parameters.get('quality')
        if quality is not None:
            try:
                quality = int(quality)
                if not 1 <= quality <= 100:
                    return False, "Quality must be between 1 and 100"
            except (ValueError, TypeError):
                return False, "Quality must be an integer"
        
        # Validate resize parameters (if provided)
        width = parameters.get('width')
        height = parameters.get('height')
        if width is not None:
            try:
                width = int(width)
                if width <= 0:
                    return False, "Width must be positive"
            except (ValueError, TypeError):
                return False, "Width must be an integer"
        
        if height is not None:
            try:
                height = int(height)
                if height <= 0:
                    return False, "Height must be positive"
            except (ValueError, TypeError):
                return False, "Height must be an integer"
        
        return True, None
    
    def process(
        self,
        input_file: UploadedFile,
        parameters: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Convert image to target format with optional resizing.
        
        Returns:
            Tuple of (output_file_path, output_filename)
        """
        output_format = parameters['output_format'].lower()
        quality = int(parameters.get('quality', 85))
        resize_width = parameters.get('width')
        resize_height = parameters.get('height')
        
        temp_input = None
        temp_output = None
        
        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(input_file.name).suffix) as tmp_in:
                for chunk in input_file.chunks():
                    tmp_in.write(chunk)
                temp_input = tmp_in.name
            
            # Open image (with HEIC support)
            try:
                # Try to register HEIF opener for HEIC files
                import pillow_heif
                pillow_heif.register_heif_opener()
            except ImportError:
                # HEIC support not available, will fall back to Pillow default
                pass
            
            with Image.open(temp_input) as img:
                original_size = img.size
                self.logger.info(f"Original image size: {original_size[0]}x{original_size[1]}")
                
                # Handle resizing if requested
                if resize_width or resize_height:
                    if resize_width and resize_height:
                        new_size = (int(resize_width), int(resize_height))
                    elif resize_width:
                        # Maintain aspect ratio based on width
                        ratio = int(resize_width) / img.size[0]
                        new_size = (int(resize_width), int(img.size[1] * ratio))
                    else:
                        # Maintain aspect ratio based on height
                        ratio = int(resize_height) / img.size[1]
                        new_size = (int(img.size[0] * ratio), int(resize_height))
                    
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    self.logger.info(f"Resized to: {new_size[0]}x{new_size[1]}")
                
                # Handle transparency and color modes
                pil_format = self.SUPPORTED_FORMATS[output_format]['format']
                
                # Convert RGBA to RGB for formats that don't support transparency
                if pil_format in ['JPEG', 'BMP', 'PPM'] and img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        rgb_img.paste(img, mask=img.split()[-1])
                    else:
                        rgb_img.paste(img)
                    img = rgb_img
                elif pil_format == 'GIF' and img.mode not in ('P', 'L'):
                    # Convert to palette mode for GIF
                    img = img.convert('P', palette=Image.Palette.ADAPTIVE)
                elif pil_format == 'PGM' and img.mode != 'L':
                    # Convert to grayscale for PGM
                    img = img.convert('L')
                elif pil_format == 'PBM' and img.mode != '1':
                    # Convert to 1-bit for PBM
                    img = img.convert('1')
                
                # Create output file
                output_filename = f"{Path(input_file.name).stem}.{output_format}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{output_format}') as tmp_out:
                    temp_output = tmp_out.name
                
                # Save with format-specific options
                save_kwargs = {'format': pil_format}
                
                if pil_format == 'JPEG':
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                elif pil_format == 'PNG':
                    save_kwargs['optimize'] = True
                elif pil_format == 'WEBP':
                    save_kwargs['quality'] = quality
                    save_kwargs['method'] = 6  # Better compression
                elif pil_format == 'TIFF':
                    save_kwargs['compression'] = 'tiff_deflate'
                
                img.save(temp_output, **save_kwargs)
            
            output_size = os.path.getsize(temp_output)
            self.logger.info(f"Successfully converted {input_file.name} to {output_format} ({output_size / 1024:.1f} KB)")
            
            # Cleanup input temp file
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            
            return temp_output, output_filename
        
        except Exception as e:
            self.logger.error(f"Image conversion failed: {e}", exc_info=True)
            
            # Cleanup on error
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)
            
            raise ToolExecutionError(f"Image conversion failed: {str(e)}")
    
    def cleanup(self, *file_paths: str) -> None:
        """Remove temporary files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
