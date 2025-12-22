"""
Azure Blob Storage client for file handling.

Supports both local development (Azurite) and production (Managed Identity).
"""

import logging
import os
from pathlib import Path
from typing import Optional

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from django.conf import settings

logger = logging.getLogger(__name__)


class BlobStorageClient:
    """
    Client for Azure Blob Storage operations.

    Automatically uses connection string for local development (Azurite)
    or Managed Identity for production deployment.
    """

    def __init__(self):
        """Initialize blob service client."""
        self._client = None

    def get_blob_service_client(self) -> BlobServiceClient:
        """
        Get or create blob service client with appropriate authentication.

        Returns:
            BlobServiceClient instance

        Raises:
            ValueError: If neither connection string nor account name is configured
        """
        if self._client is not None:
            return self._client

        connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

        if connection_string:
            # Local development with Azurite
            logger.info("🔗 Using Azurite connection string for blob storage")
            self._client = BlobServiceClient.from_connection_string(connection_string)
        else:
            # Production with Managed Identity
            account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None)
            if not account_name:
                raise ValueError(
                    "Either AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_NAME must be configured"
                )

            logger.info(f"🔐 Using Managed Identity for blob storage: {account_name}")
            account_url = f"https://{account_name}.blob.core.windows.net"
            credential = DefaultAzureCredential()
            self._client = BlobServiceClient(account_url, credential=credential)

        return self._client

    def upload_file(
        self, container_name: str, blob_path: str, file_path: str
    ) -> str:
        """
        Upload file to blob storage.

        Args:
            container_name: Target container (uploads, processed, temp)
            blob_path: Blob path within container (e.g., "video/12345.mp4")
            file_path: Local file path to upload

        Returns:
            Full blob URL

        Raises:
            AzureError: If upload fails
        """
        try:
            client = self.get_blob_service_client()
            blob_client = client.get_blob_client(container=container_name, blob=blob_path)

            logger.info(f"📤 Uploading to {container_name}/{blob_path}")

            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            blob_url = blob_client.url
            logger.info(f"✅ Upload complete: {blob_url}")

            return blob_url

        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            raise

    def download_file(
        self, container_name: str, blob_path: str, local_path: str
    ) -> str:
        """
        Download file from blob storage.

        Args:
            container_name: Source container
            blob_path: Blob path within container
            local_path: Local destination path

        Returns:
            Local file path

        Raises:
            AzureError: If download fails
        """
        try:
            client = self.get_blob_service_client()
            blob_client = client.get_blob_client(container=container_name, blob=blob_path)

            logger.info(f"📥 Downloading from {container_name}/{blob_path}")

            # Ensure parent directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            with open(local_path, "wb") as download_file:
                download_stream = blob_client.download_blob()
                download_file.write(download_stream.readall())

            logger.info(f"✅ Download complete: {local_path}")

            return local_path

        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            raise

    def delete_file(self, container_name: str, blob_path: str) -> bool:
        """
        Delete file from blob storage.

        Args:
            container_name: Container name
            blob_path: Blob path within container

        Returns:
            True if deleted successfully

        Raises:
            AzureError: If deletion fails
        """
        try:
            client = self.get_blob_service_client()
            blob_client = client.get_blob_client(container=container_name, blob=blob_path)

            logger.info(f"🗑️ Deleting {container_name}/{blob_path}")

            blob_client.delete_blob()

            logger.info(f"✅ Deletion complete")

            return True

        except Exception as e:
            logger.error(f"❌ Deletion failed: {e}")
            raise

    def get_blob_url(self, container_name: str, blob_path: str) -> str:
        """
        Get public URL for blob.

        Args:
            container_name: Container name
            blob_path: Blob path within container

        Returns:
            Full blob URL
        """
        client = self.get_blob_service_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_path)
        return blob_client.url

    def blob_exists(self, container_name: str, blob_path: str) -> bool:
        """
        Check if blob exists.

        Args:
            container_name: Container name
            blob_path: Blob path within container

        Returns:
            True if blob exists
        """
        try:
            client = self.get_blob_service_client()
            blob_client = client.get_blob_client(container=container_name, blob=blob_path)
            return blob_client.exists()
        except Exception as e:
            logger.error(f"❌ Error checking blob existence: {e}")
            return False
