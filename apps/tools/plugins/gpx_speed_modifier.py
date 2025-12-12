"""
GPX Speed Modifier tool.

Modifies track speeds in GPX files while preserving distance and elevation data.
Recalculates timestamps based on speed multiplier.
Uses Azure Functions for async processing.
"""

import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError
from apps.tools.base import BaseTool

try:
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    AzureCliCredential = None
    DefaultAzureCredential = None
    BlobServiceClient = None


class GPXSpeedModifier(BaseTool):
    """
    Modify GPX track speeds by adjusting timestamps.

    Changes track speed by applying a multiplier to recalculate timestamps
    while preserving the geographical path.
    Uses async processing via Azure Functions for scalability.
    """

    # Tool metadata
    name = "gpx-speed-modifier"
    display_name = "GPX Speed Modifier"
    description = (
        "Modify GPS track speeds by adjusting timestamps while preserving the exact geographical path and elevation profile. "
        "Supports speed multipliers from 0.1x to 10x, perfect for training scenarios, pace simulation, and GPS timing corrections."
    )
    category = "file"
    version = "1.0.0"
    icon = "speedometer2"

    # File constraints
    allowed_input_types = [".gpx"]
    max_file_size = 50 * 1024 * 1024  # 50MB

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and parameters.

        Required parameters:
        - speed_multiplier: Float multiplier for speed (0.5 = half speed, 2.0 = double speed)
        """
        # Validate file type
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"

        # Validate file size
        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"

        # Validate speed_multiplier
        speed_multiplier = parameters.get("speed_multiplier")
        if speed_multiplier is None:
            return False, "Missing required parameter: speed_multiplier"

        try:
            speed_multiplier = float(speed_multiplier)
            if not 0.1 <= speed_multiplier <= 10.0:
                return False, "Speed multiplier must be between 0.1 and 10.0"
        except (ValueError, TypeError):
            return False, "Speed multiplier must be a number"

        return True, None

    def process(
        self, input_file: UploadedFile, parameters: Dict[str, Any], execution_id: str = None
    ) -> Tuple[str, Optional[str]]:
        """
        Upload GPX file to Azure Blob Storage for async processing.

        This method only uploads the file. The actual modification is done by Azure Function.

        Args:
            input_file: Uploaded GPX file
            parameters: Must contain 'speed_multiplier' key
            execution_id: Optional execution ID (generated if not provided)

        Returns:
            Tuple of (execution_id, None) - None indicates async processing

        Raises:
            ToolExecutionError: If upload fails
        """
        speed_multiplier = float(parameters["speed_multiplier"])

        # Generate execution ID if not provided
        if not execution_id:
            execution_id = str(uuid.uuid4())

        try:
            self.logger.info("=" * 80)
            self.logger.info("📤 STARTING GPX UPLOAD FOR ASYNC PROCESSING")
            self.logger.info(f"   Execution ID: {execution_id}")
            self.logger.info(f"   Original filename: {input_file.name}")
            self.logger.info(f"   File size: {input_file.size:,} bytes")
            self.logger.info(f"   Speed multiplier: {speed_multiplier}x")
            self.logger.info("=" * 80)

            # Get blob service client
            blob_service = self._get_blob_service_client()

            # Upload to gpx container
            blob_name = f"gpx/{execution_id}.gpx"
            blob_client = blob_service.get_blob_client(
                container="uploads",
                blob=blob_name
            )

            # Prepare metadata for Azure Function
            metadata = {
                "execution_id": execution_id,
                "original_filename": input_file.name,
                "speed_multiplier": str(speed_multiplier),
                "file_size": str(input_file.size),
            }

            self.logger.info(f"📋 Blob metadata prepared: {metadata}")

            # Upload file
            self.logger.info(f"⬆️  Uploading GPX file to blob storage: {blob_name}")
            file_content = input_file.read()
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                metadata=metadata
            )

            self.logger.info("✅ GPX file uploaded successfully to Azure Blob Storage")
            self.logger.info(f"   Blob name: {blob_name}")
            self.logger.info(f"   Container: uploads")
            self.logger.info(f"   Size: {len(file_content):,} bytes")

            # Trigger Azure Function via HTTP (workaround for Flex Consumption blob trigger limitations)
            self.logger.info("=" * 80)
            self.logger.info("🚀 TRIGGERING AZURE FUNCTION FOR GPX SPEED MODIFICATION")
            try:
                import requests
                import threading
                base_url = getattr(settings, "AZURE_FUNCTION_BASE_URL", None)
                
                if base_url:
                    # Construct full URL by appending endpoint
                    function_url = f"{base_url}/gpx/speed"
                    payload = {
                        "execution_id": execution_id,
                        "blob_name": f"uploads/{blob_name}"  # Full path: uploads/gpx/{uuid}.gpx
                    }
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
            self.logger.error(f"❌ Failed to upload GPX file: {e}")
            raise ToolExecutionError(f"GPX file upload failed: {str(e)}")

    def _get_blob_service_client(self) -> BlobServiceClient:
        """
        Get Azure Blob Storage client.

        Uses connection string for local Azurite, DefaultAzureCredential for Azure.
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
        Get tool metadata including speed options.

        Returns:
            Dictionary with tool information and speed options
        """
        metadata = super().get_metadata()
        metadata["speedOptions"] = [
            {"value": "0.5", "label": "Half Speed (0.5x)"},
            {"value": "0.75", "label": "Three-Quarter Speed (0.75x)"},
            {"value": "1.5", "label": "1.5x Speed"},
            {"value": "2.0", "label": "Double Speed (2x)"},
            {"value": "3.0", "label": "Triple Speed (3x)"},
            {"value": "5.0", "label": "5x Speed"},
        ]
        return metadata
