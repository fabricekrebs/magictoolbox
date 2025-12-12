"""
Image format converter tool.

Converts images between different formats (e.g., PNG to JPG, WEBP to PNG).
Uses Azure Functions with Pillow for async image processing.
"""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError, ToolValidationError
from apps.tools.base import BaseTool

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    AzureCliCredential = None
    DefaultAzureCredential = None
    BlobServiceClient = None


class ImageFormatConverter(BaseTool):
    """
    Convert images between different formats.

    Supports: JPG, PNG, WEBP, BMP, GIF, TIFF, ICO, TGA, PPM, PGM, PBM
    Uses async processing via Azure Functions for scalability.
    """

    # Tool metadata
    name = "image-format-converter"
    display_name = "Image Format Converter"
    description = (
        "Convert images between all common formats including JPG, PNG, WEBP, BMP, GIF, TIFF, and ICO. "
        "Supports both single file and bulk conversion with quality preservation."
    )
    category = "image"
    version = "2.0.0"
    icon = "image"

    # File constraints
    allowed_input_types = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".gif",
        ".tiff",
        ".tif",
        ".ico",
        ".tga",
        ".ppm",
        ".pgm",
        ".pbm",
        ".pcx",
        ".sgi",
        ".im",
        ".msp",
        ".dib",
        ".xbm",
        ".eps",
        ".heic",
        ".heif",  # Apple's HEIC/HEIF format
    ]
    max_file_size = 50 * 1024 * 1024  # 50MB per file

    # Supported output formats with descriptions
    SUPPORTED_FORMATS = {
        "jpg": {
            "format": "JPEG",
            "name": "JPEG",
            "description": "Best for photos, lossy compression",
        },
        "jpeg": {
            "format": "JPEG",
            "name": "JPEG",
            "description": "Best for photos, lossy compression",
        },
        "png": {"format": "PNG", "name": "PNG", "description": "Lossless, supports transparency"},
        "webp": {
            "format": "WEBP",
            "name": "WebP",
            "description": "Modern format, great compression",
        },
        "bmp": {"format": "BMP", "name": "BMP", "description": "Uncompressed, large file size"},
        "gif": {
            "format": "GIF",
            "name": "GIF",
            "description": "Supports animation, limited colors",
        },
        "tiff": {"format": "TIFF", "name": "TIFF", "description": "High quality, large files"},
        "tif": {"format": "TIFF", "name": "TIFF", "description": "High quality, large files"},
        "ico": {"format": "ICO", "name": "ICO", "description": "Icon format, multiple sizes"},
        "tga": {"format": "TGA", "name": "TGA", "description": "Targa format"},
        "ppm": {"format": "PPM", "name": "PPM", "description": "Portable Pixmap"},
        "pgm": {"format": "PGM", "name": "PGM", "description": "Portable Graymap"},
        "pbm": {"format": "PBM", "name": "PBM", "description": "Portable Bitmap"},
        "heic": {"format": "HEIC", "name": "HEIC", "description": "Apple High Efficiency Image"},
        "heif": {"format": "HEIF", "name": "HEIF", "description": "High Efficiency Image Format"},
    }

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
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
        output_format = parameters.get("output_format", "").lower()
        if not output_format:
            return False, "Missing required parameter: output_format"

        if output_format not in self.SUPPORTED_FORMATS:
            return (
                False,
                f"Unsupported output format: {output_format}. Supported: {', '.join(self.SUPPORTED_FORMATS.keys())}",
            )

        # Validate quality parameter (if provided)
        quality = parameters.get("quality")
        if quality is not None:
            try:
                quality = int(quality)
                if not 1 <= quality <= 100:
                    return False, "Quality must be between 1 and 100"
            except (ValueError, TypeError):
                return False, "Quality must be an integer"

        # Validate resize parameters (if provided)
        width = parameters.get("width")
        height = parameters.get("height")
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
        self, input_file: UploadedFile, parameters: Dict[str, Any], execution_id: str = None
    ) -> Tuple[str, Optional[str]]:
        """
        Upload image to Azure Blob Storage for async processing.

        This method only uploads the file. The actual conversion is done by Azure Function.

        Args:
            input_file: Uploaded image file
            parameters: Must contain 'output_format' key, optionally 'quality', 'width', 'height'
            execution_id: Optional execution ID (generated if not provided)

        Returns:
            Tuple of (execution_id, None) - None indicates async processing

        Raises:
            ToolExecutionError: If upload fails
        """
        output_format = parameters.get("output_format", "").lower()
        quality = int(parameters.get("quality", 85))
        resize_width = parameters.get("width")
        resize_height = parameters.get("height")

        # Generate execution ID if not provided
        if not execution_id:
            execution_id = str(uuid.uuid4())

        try:
            self.logger.info("=" * 80)
            self.logger.info("📤 STARTING IMAGE UPLOAD FOR ASYNC PROCESSING")
            self.logger.info(f"   Execution ID: {execution_id}")
            self.logger.info(f"   Original filename: {input_file.name}")
            self.logger.info(f"   File size: {input_file.size:,} bytes")
            self.logger.info(f"   Output format: {output_format}")
            self.logger.info(f"   Quality: {quality}")
            self.logger.info("=" * 80)

            # Get blob service client
            blob_service = self._get_blob_service_client()

            # Upload to image uploads container
            file_ext = Path(input_file.name).suffix
            blob_name = f"image/{execution_id}{file_ext}"
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=blob_name
            )

            # Prepare metadata for Azure Function
            metadata = {
                "execution_id": execution_id,
                "original_filename": input_file.name,
                "output_format": output_format,
                "quality": str(quality),
                "file_size": str(input_file.size),
            }
            if resize_width:
                metadata["width"] = str(resize_width)
            if resize_height:
                metadata["height"] = str(resize_height)

            self.logger.info(f"📋 Blob metadata prepared: {metadata}")

            # Upload file
            self.logger.info(f"⬆️  Uploading image to blob storage: {blob_name}")
            file_content = input_file.read()
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                metadata=metadata
            )

            self.logger.info("✅ Image uploaded successfully to Azure Blob Storage")
            self.logger.info(f"   Blob name: {blob_name}")
            self.logger.info(f"   Container: uploads")
            self.logger.info(f"   Size: {len(file_content):,} bytes")

            # Trigger Azure Function via HTTP (workaround for Flex Consumption blob trigger limitations)
            self.logger.info("=" * 80)
            self.logger.info("🚀 TRIGGERING AZURE FUNCTION FOR IMAGE CONVERSION")
            try:
                import requests
                import threading
                base_url = getattr(settings, "AZURE_FUNCTION_BASE_URL", None)
                
                if base_url:
                    # Construct full URL by appending endpoint
                    function_url = f"{base_url}/image/convert"
                    payload = {
                        "execution_id": execution_id,
                        "blob_name": f"uploads/{blob_name}",  # Full path: uploads/image/{uuid}.ext
                        "output_format": output_format,
                        "quality": quality
                    }
                    # Add optional resize parameters if provided
                    if resize_width:
                        payload["width"] = resize_width
                    if resize_height:
                        payload["height"] = resize_height
                    self.logger.info(f"   Function URL: {function_url}")
                    self.logger.info(f"   Payload: {payload}")
                    self.logger.info(f"   Sending async POST request...")
                    
                    # Use a background thread to avoid blocking the upload response
                    def trigger_function_async():
                        """Background thread to trigger Azure Function."""
                        try:
                            response = requests.post(function_url, json=payload, timeout=300)
                            self.logger.info(f"📨 Response received from Azure Function")
                            self.logger.info(f"   Status code: {response.status_code}")
                            
                            if response.status_code == 200:
                                self.logger.info("✅ Azure Function triggered successfully")
                            else:
                                self.logger.warning(
                                    f"⚠️  Azure Function returned non-200 status: {response.status_code}"
                                )
                        except Exception as e:
                            self.logger.error(f"❌ Azure Function call failed in background: {e}")
                    
                    # Start background thread and return immediately
                    thread = threading.Thread(target=trigger_function_async, daemon=True)
                    thread.start()
                    self.logger.info("✅ Azure Function trigger started in background thread")
                else:
                    self.logger.warning(
                        "⚠️  AZURE_FUNCTION_BASE_URL not configured. "
                        "Relying on blob trigger (may not work with Flex Consumption)."
                    )
            except Exception as http_error:
                self.logger.error(f"❌ Failed to trigger Azure Function via HTTP: {http_error}")
                # Don't fail the upload - the blob trigger might still work

            # Return execution_id and None to indicate async processing
            return execution_id, None

        except Exception as e:
            self.logger.error(f"❌ Failed to upload image: {e}")
            raise ToolExecutionError(f"Image upload failed: {str(e)}")

    def _get_blob_service_client(self) -> BlobServiceClient:
        """
        Get Azure Blob Storage client.

        Uses connection string for local Azurite, DefaultAzureCredential for Azure.
        This matches the pattern used in PDF converter.
        """
        connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

        # Check for local development (Azurite)
        if connection_string and "127.0.0.1" in connection_string:
            self.logger.info("🔧 Using local Azurite for blob storage")
            return BlobServiceClient.from_connection_string(connection_string)

        # Production: Use Managed Identity / DefaultAzureCredential
        storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None) or getattr(
            settings, "AZURE_ACCOUNT_NAME", None
        )
        if not storage_account_name:
            self.logger.error("❌ Storage account name not configured")
            raise ToolExecutionError(
                "AZURE_STORAGE_ACCOUNT_NAME or AZURE_ACCOUNT_NAME not configured for production environment"
            )

        account_url = f"https://{storage_account_name}.blob.core.windows.net"

        # Use AzureCliCredential for local/testing, DefaultAzureCredential for production
        use_cli_auth = os.getenv("USE_AZURE_CLI_AUTH", "false").lower() == "true" or settings.DEBUG

        if use_cli_auth:
            self.logger.info(
                f"🔐 Using Azure CLI credential for storage account: {storage_account_name}"
            )
            credential = AzureCliCredential()
        else:
            self.logger.info(
                f"🔐 Using Azure Managed Identity for storage account: {storage_account_name}"
            )
            credential = DefaultAzureCredential()

        return BlobServiceClient(account_url=account_url, credential=credential)

    def cleanup(self, *file_paths: str) -> None:
        """
        Remove temporary files (not used in async mode).

        Args:
            *file_paths: Paths to files to remove
        """
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup {file_path}: {e}")

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get tool metadata including format options.

        Returns:
            Dictionary with tool information and format options
        """
        metadata = super().get_metadata()
        metadata["formatOptions"] = [
            {
                "value": key,
                "label": config["name"],
                "description": config["description"],
            }
            for key, config in self.SUPPORTED_FORMATS.items()
            if key not in ["jpeg", "tif"]  # Skip aliases
        ]
        return metadata
