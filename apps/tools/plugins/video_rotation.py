"""
Video rotation tool.

Rotates video files by 90° clockwise, 90° counter-clockwise, or 180°.
Uses Azure Functions with FFmpeg for async video processing.
"""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from azure.identity import AzureCliCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from apps.core.exceptions import ToolExecutionError, ToolValidationError
from apps.tools.base import BaseTool


class VideoRotation(BaseTool):
    """
    Rotate video files by specified angles.

    Supports: MP4, AVI, MOV, MKV, WEBM, FLV
    Rotation options: 90° clockwise, 90° counter-clockwise, 180°
    """

    # Tool metadata
    name = "video-rotation"
    display_name = "Video Rotation"
    description = (
        "Rotate video files by 90° clockwise, 90° counter-clockwise, or 180°. "
        "Preserves video quality and audio tracks. Supports all common video formats."
    )
    category = "video"
    version = "1.0.0"
    icon = "arrow-clockwise"

    # File constraints
    allowed_input_types = [
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".webm",
        ".flv",
        ".wmv",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".3gp",
    ]
    max_file_size = 500 * 1024 * 1024  # 500MB

    # Rotation angles and FFmpeg transpose parameters
    ROTATION_ANGLES = {
        "90_cw": {
            "name": "90° Clockwise",
            "transpose": "1",
            "description": "Rotate 90 degrees clockwise",
        },
        "90_ccw": {
            "name": "90° Counter-Clockwise",
            "transpose": "2",
            "description": "Rotate 90 degrees counter-clockwise",
        },
        "180": {
            "name": "180°",
            "transpose": "2,transpose=2",
            "description": "Rotate 180 degrees (flip upside down)",
        },
    }

    def __init__(self):
        """Initialize tool."""
        super().__init__()

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and rotation parameters.

        Args:
            input_file: Uploaded video file
            parameters: Must contain 'rotation' key with valid angle

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        if input_file.size > self.max_file_size:
            return False, f"File size exceeds maximum of {self.max_file_size / (1024 * 1024):.0f}MB"

        # Check file extension
        file_ext = Path(input_file.name).suffix.lower()
        if file_ext not in self.allowed_input_types:
            return False, f"Unsupported file type: {file_ext}. Allowed: {', '.join(self.allowed_input_types)}"

        # Check rotation parameter
        rotation = parameters.get("rotation")
        if not rotation:
            return False, "Rotation angle is required"

        if rotation not in self.ROTATION_ANGLES:
            valid_rotations = ", ".join(self.ROTATION_ANGLES.keys())
            return False, f"Invalid rotation angle. Valid options: {valid_rotations}"

        return True, None

    def process(
        self, input_file: UploadedFile, parameters: Dict[str, Any], execution_id: str = None
    ) -> Tuple[str, Optional[str]]:
        """
        Upload video to Azure Blob Storage for async processing.

        This method only uploads the file. The actual rotation is done by Azure Function.

        Args:
            input_file: Uploaded video file
            parameters: Must contain 'rotation' key
            execution_id: Optional execution ID (generated if not provided)

        Returns:
            Tuple of (execution_id, None) - None indicates async processing

        Raises:
            ToolExecutionError: If upload fails
        """
        rotation = parameters.get("rotation")
        
        # Generate execution ID if not provided
        if not execution_id:
            execution_id = str(uuid.uuid4())

        try:
            self.logger.info(f"Uploading video for rotation: {input_file.name}")
            self.logger.info(f"Execution ID: {execution_id}")
            self.logger.info(f"Rotation: {rotation}")

            # Get blob service client
            blob_service = self._get_blob_service_client()

            # Upload to video-uploads container
            blob_name = f"{execution_id}{Path(input_file.name).suffix}"
            blob_client = blob_service.get_blob_client(
                container="video-uploads",
                blob=blob_name
            )

            # Upload file with metadata
            metadata = {
                "execution_id": execution_id,
                "original_filename": input_file.name,
                "rotation": rotation,
                "file_size": str(input_file.size),
            }

            self.logger.info(f"Uploading to blob: {blob_name}")
            file_content = input_file.read()
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                metadata=metadata
            )

            self.logger.info(f"✅ Video uploaded successfully to Azure Blob Storage")
            self.logger.info(f"   Blob name: {blob_name}")
            self.logger.info(f"   Container: video-uploads")
            self.logger.info(f"   Size: {len(file_content):,} bytes")

            # Note: Azure Function trigger happens in the rotate-video endpoint
            # This is just the upload step - rotation is triggered separately by user action

            # Return execution_id and None to indicate async processing
            return execution_id, None

        except Exception as e:
            self.logger.error(f"Failed to upload video: {e}")
            raise ToolExecutionError(f"Video upload failed: {str(e)}")

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
        storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None)
        if not storage_account_name:
            self.logger.error("❌ Storage account name not configured")
            raise ToolExecutionError(
                "AZURE_STORAGE_ACCOUNT_NAME not configured for production environment"
            )

        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        
        # Use AzureCliCredential for local/testing, DefaultAzureCredential for production
        # Check for explicit flag or if running in local development
        use_cli_auth = os.getenv("USE_AZURE_CLI_AUTH", "false").lower() == "true" or settings.DEBUG
        
        if use_cli_auth:
            self.logger.info(f"🔐 Using Azure CLI credential for storage account: {storage_account_name}")
            credential = AzureCliCredential()
        else:
            self.logger.info(f"🔐 Using Azure Managed Identity for storage account: {storage_account_name}")
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
        Get tool metadata including rotation options.

        Returns:
            Dictionary with tool information and rotation options
        """
        metadata = super().get_metadata()
        metadata["rotationOptions"] = [
            {
                "value": key,
                "label": config["name"],
                "description": config["description"],
            }
            for key, config in self.ROTATION_ANGLES.items()
        ]
        return metadata
