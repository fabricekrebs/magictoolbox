"""
GPX Merger tool.

Combines multiple GPX files into a single GPX file, preserving all tracks, routes, and waypoints.
Uses Azure Functions for async processing of multiple files.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError, ToolValidationError
from apps.tools.base import BaseTool

try:
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    AzureCliCredential = None
    DefaultAzureCredential = None
    BlobServiceClient = None


class GPXMerger(BaseTool):
    """
    Merge multiple GPX files into a single GPX file.

    Combines tracks, routes, and waypoints from multiple GPS files.
    Uses async processing via Azure Functions for scalability.
    """

    # Tool metadata
    name = "gpx-merger"
    display_name = "GPX Merger"
    description = (
        "Combine multiple GPX files into one unified track. "
        "Merges all waypoints, tracks, and routes while preserving metadata. "
        "Perfect for combining daily rides, multi-day hikes, or segmented routes into a complete journey."
    )
    category = "file"
    version = "1.0.0"
    icon = "link-45deg"

    # File constraints
    allowed_input_types = [".gpx"]
    max_file_size = 50 * 1024 * 1024  # 50MB per file
    min_files = 2  # Must upload at least 2 files
    max_files = 20  # Maximum 20 files per merge

    def __init__(self):
        """Initialize GPX Merger with logging."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate individual GPX file.

        This validates each file in a multi-file upload.
        Full validation of file count happens in validate_multiple().

        Args:
            input_file: Uploaded GPX file
            parameters: Merge parameters

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate file type
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"

        # Validate file size
        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"

        return True, None

    def validate_multiple(
        self, input_files: List[UploadedFile], parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate multiple files for merging.

        Args:
            input_files: List of uploaded GPX files
            parameters: Merge parameters

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file count
        if len(input_files) < self.min_files:
            return False, f"At least {self.min_files} files required for merging"

        if len(input_files) > self.max_files:
            return False, f"Maximum {self.max_files} files allowed per merge operation"

        # Validate each file individually
        for input_file in input_files:
            is_valid, error_msg = self.validate(input_file, parameters)
            if not is_valid:
                return False, f"File '{input_file.name}': {error_msg}"

        # Validate merge mode parameter
        merge_mode = parameters.get("merge_mode", "chronological")
        valid_modes = ["chronological", "sequential", "preserve_order"]
        if merge_mode not in valid_modes:
            return False, f"Invalid merge_mode. Must be one of: {', '.join(valid_modes)}"

        return True, None

    def process(
        self, input_file: UploadedFile, parameters: Dict[str, Any], execution_id: str = None
    ) -> Tuple[str, None]:
        """
        Single file upload not supported - use process_multiple() instead.

        Args:
            input_file: Uploaded file (not used)
            parameters: Processing parameters (not used)
            execution_id: Execution ID (not used)

        Raises:
            ToolExecutionError: Always raises error directing to use multiple files
        """
        raise ToolExecutionError(
            "GPX Merger requires multiple files. Please upload at least 2 GPX files."
        )

    def process_multiple(
        self, input_files: List[UploadedFile], parameters: Dict[str, Any]
    ) -> List[Tuple[str, str]]:
        """
        Upload multiple GPX files to Azure Blob Storage for async merging.

        This method uploads all files and triggers Azure Function for processing.

        Args:
            input_files: List of uploaded GPX files
            parameters: Must contain 'merge_mode' key (optional)

        Returns:
            List with single tuple: [(execution_id, "merged.gpx")]

        Raises:
            ToolExecutionError: If upload or trigger fails
        """
        # Generate single execution ID for the entire merge operation
        execution_id = str(uuid.uuid4())
        merge_mode = parameters.get("merge_mode", "chronological")
        output_name = parameters.get("output_name", "merged_track")

        try:
            self.logger.info("=" * 80)
            self.logger.info("📤 STARTING MULTI-FILE GPX UPLOAD FOR MERGE OPERATION")
            self.logger.info(f"   Execution ID: {execution_id}")
            self.logger.info(f"   Number of files: {len(input_files)}")
            self.logger.info(f"   Merge mode: {merge_mode}")
            self.logger.info(f"   Output name: {output_name}")
            self.logger.info("=" * 80)

            # Get blob service client
            blob_service = self._get_blob_service_client()

            # Upload all files to blob storage with sequential naming
            uploaded_blobs = []
            total_size = 0

            for idx, input_file in enumerate(input_files):
                file_ext = Path(input_file.name).suffix
                blob_name = f"{execution_id}_{idx:03d}{file_ext}"

                self.logger.info(
                    f"📦 Uploading file {idx + 1}/{len(input_files)}: {input_file.name}"
                )
                self.logger.info(f"   Target blob: {blob_name}")
                self.logger.info(f"   File size: {input_file.size:,} bytes")

                blob_client = blob_service.get_blob_client(container="gpx-uploads", blob=blob_name)

                # Prepare metadata for each file
                metadata = {
                    "execution_id": execution_id,
                    "original_filename": input_file.name,
                    "file_index": str(idx),
                    "total_files": str(len(input_files)),
                    "merge_mode": merge_mode,
                    "output_name": output_name,
                }

                # Upload file
                file_content = input_file.read()
                blob_client.upload_blob(file_content, overwrite=True, metadata=metadata)

                uploaded_blobs.append(blob_name)
                total_size += len(file_content)

                self.logger.info("   ✅ Uploaded successfully")

            self.logger.info("=" * 80)
            self.logger.info(f"✅ ALL {len(input_files)} FILES UPLOADED SUCCESSFULLY")
            self.logger.info(
                f"   Total size: {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)"
            )
            self.logger.info(f"   Uploaded blobs: {len(uploaded_blobs)}")
            self.logger.info("=" * 80)

            # Trigger Azure Function via HTTP
            self.logger.info("🚀 TRIGGERING AZURE FUNCTION FOR GPX MERGE")

            try:
                import threading

                import requests

                base_url = getattr(settings, "AZURE_FUNCTION_BASE_URL", None)

                if base_url:
                    # Construct full URL
                    function_url = f"{base_url}/gpx/merge"

                    # Prepare payload with all blob names
                    payload = {
                        "execution_id": execution_id,
                        "blob_names": [f"gpx-uploads/{blob}" for blob in uploaded_blobs],
                        "merge_mode": merge_mode,
                        "output_name": output_name,
                        "file_count": len(input_files),
                    }

                    self.logger.info(f"   Function URL: {function_url}")
                    self.logger.info(f"   Payload: {payload}")
                    self.logger.info("   Sending async POST request...")

                    # Use background thread to avoid blocking
                    def trigger_function():
                        try:
                            response = requests.post(function_url, json=payload, timeout=10)
                            self.logger.info(
                                f"   ✅ Azure Function triggered: {response.status_code}"
                            )
                        except Exception as e:
                            self.logger.error(f"   ⚠️  Failed to trigger Azure Function: {e}")

                    thread = threading.Thread(target=trigger_function)
                    thread.daemon = True
                    thread.start()

                    self.logger.info("   🎯 Background trigger initiated")
                else:
                    self.logger.warning(
                        "   ⚠️  AZURE_FUNCTION_BASE_URL not configured - skipping trigger"
                    )
                    self.logger.warning(
                        "   Azure Function will need manual triggering or blob trigger"
                    )

            except ImportError:
                self.logger.warning(
                    "   ⚠️  'requests' library not available - skipping HTTP trigger"
                )
            except Exception as e:
                self.logger.warning(f"   ⚠️  Failed to trigger Azure Function: {e}")

            self.logger.info("=" * 80)
            self.logger.info("📋 MERGE OPERATION SUMMARY")
            self.logger.info("   Status: Pending (async processing)")
            self.logger.info(f"   Execution ID: {execution_id}")
            self.logger.info(f"   Files merged: {len(input_files)}")
            self.logger.info(f"   Expected output: {output_name}.gpx")
            self.logger.info("=" * 80)

            # Return single execution result
            # Frontend will poll for status using this execution_id
            return [(execution_id, f"{output_name}.gpx")]

        except Exception as e:
            self.logger.error(f"GPX merge upload failed: {e}", exc_info=True)
            raise ToolExecutionError(f"Failed to upload files for merging: {str(e)}")

    def _get_blob_service_client(self) -> "BlobServiceClient":
        """
        Get Azure Blob Storage client with support for both Azurite (local) and Azure (production).

        Returns:
            BlobServiceClient instance

        Raises:
            ToolExecutionError: If Azure SDK not installed or configuration missing
        """
        if BlobServiceClient is None:
            raise ToolExecutionError(
                "Azure SDK not installed. Install azure-storage-blob and azure-identity."
            )

        # Detect environment and get appropriate client
        connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

        if connection_string and "127.0.0.1" in connection_string:
            # Local development with Azurite
            self.logger.info("🔧 Using local Azurite for blob storage")
            return BlobServiceClient.from_connection_string(connection_string)
        else:
            # Production with Azure Managed Identity
            storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None) or getattr(
                settings, "AZURE_ACCOUNT_NAME", None
            )
            if not storage_account_name:
                raise ToolExecutionError(
                    "AZURE_STORAGE_ACCOUNT_NAME or AZURE_ACCOUNT_NAME not configured"
                )

            account_url = f"https://{storage_account_name}.blob.core.windows.net"

            # Use AzureCliCredential for local/testing, DefaultAzureCredential for production
            use_cli_auth = (
                os.getenv("USE_AZURE_CLI_AUTH", "false").lower() == "true" or settings.DEBUG
            )

            if use_cli_auth:
                self.logger.info(
                    f"🔐 Using Azure CLI credential for storage: {storage_account_name}"
                )
                credential = AzureCliCredential()
            else:
                self.logger.info(
                    f"🔐 Using Azure Managed Identity for storage: {storage_account_name}"
                )
                credential = DefaultAzureCredential()

            return BlobServiceClient(account_url=account_url, credential=credential)

    def cleanup(self, *file_paths: str) -> None:
        """
        Clean up temporary files.

        For GPX Merger, cleanup is handled by Azure Function and blob lifecycle policies.
        This method is implemented to satisfy the abstract base class requirement.

        Args:
            *file_paths: Paths to temporary files (unused for async processing)
        """
        # No local cleanup needed - files are uploaded directly to blob storage
        # Azure Function handles cleanup of processed files
        # Blob lifecycle policies manage retention
        pass
