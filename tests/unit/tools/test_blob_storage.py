"""
Unit tests for BlobStorageClient.

Tests Azure Blob Storage operations with mocked Azure SDK.
"""

import os
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open

from apps.tools.services.blob_storage import BlobStorageClient


class TestBlobStorageClient:
    """Test suite for BlobStorageClient."""
    
    @patch('apps.tools.services.blob_storage.BlobServiceClient.from_connection_string')
    def test_get_blob_service_client_with_connection_string(self, mock_from_conn):
        """Test client creation with connection string (local development)."""
        mock_client = Mock()
        mock_from_conn.return_value = mock_client
        
        with patch('apps.tools.services.blob_storage.settings') as mock_settings:
            mock_settings.AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;..."
            
            client = BlobStorageClient()
            result = client.get_blob_service_client()
            
            assert result == mock_client
            mock_from_conn.assert_called_once_with("DefaultEndpointsProtocol=https;...")
    
    @patch('apps.tools.services.blob_storage.DefaultAzureCredential')
    @patch('apps.tools.services.blob_storage.BlobServiceClient')
    def test_get_blob_service_client_with_managed_identity(self, mock_blob_service, mock_credential):
        """Test client creation with Managed Identity (production)."""
        mock_client = Mock()
        mock_blob_service.return_value = mock_client
        mock_cred_instance = Mock()
        mock_credential.return_value = mock_cred_instance
        
        with patch('apps.tools.services.blob_storage.settings') as mock_settings:
            mock_settings.AZURE_STORAGE_CONNECTION_STRING = None
            mock_settings.AZURE_STORAGE_ACCOUNT_NAME = "teststorage"
            
            client = BlobStorageClient()
            result = client.get_blob_service_client()
            
            assert result == mock_client
            mock_credential.assert_called_once()
            mock_blob_service.assert_called_once_with(
                "https://teststorage.blob.core.windows.net",
                credential=mock_cred_instance
            )
    
    def test_get_blob_service_client_raises_without_config(self):
        """Test that client raises ValueError without proper configuration."""
        with patch('apps.tools.services.blob_storage.settings') as mock_settings:
            mock_settings.AZURE_STORAGE_CONNECTION_STRING = None
            mock_settings.AZURE_STORAGE_ACCOUNT_NAME = None
            
            client = BlobStorageClient()
            
            with pytest.raises(ValueError, match="Either AZURE_STORAGE_CONNECTION_STRING"):
                client.get_blob_service_client()
    
    @patch('apps.tools.services.blob_storage.BlobStorageClient.get_blob_service_client')
    @patch('builtins.open', new_callable=mock_open, read_data=b'test data')
    def test_upload_file_success(self, mock_file, mock_get_client):
        """Test successful file upload."""
        # Mock blob client
        mock_blob_client = Mock()
        mock_blob_client.url = "https://teststorage.blob.core.windows.net/uploads/test.txt"
        
        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        mock_get_client.return_value = mock_service_client
        
        client = BlobStorageClient()
        result_url = client.upload_file("uploads", "test/test.txt", "/tmp/test.txt")
        
        assert result_url == "https://teststorage.blob.core.windows.net/uploads/test.txt"
        mock_service_client.get_blob_client.assert_called_once_with(
            container="uploads",
            blob="test/test.txt"
        )
        mock_blob_client.upload_blob.assert_called_once()
    
    @patch('apps.tools.services.blob_storage.BlobStorageClient.get_blob_service_client')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_download_file_success(self, mock_makedirs, mock_file, mock_get_client):
        """Test successful file download."""
        # Mock blob download
        mock_download_stream = Mock()
        mock_download_stream.readall.return_value = b'downloaded data'
        
        mock_blob_client = Mock()
        mock_blob_client.download_blob.return_value = mock_download_stream
        
        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        mock_get_client.return_value = mock_service_client
        
        client = BlobStorageClient()
        result_path = client.download_file("uploads", "test/test.txt", "/tmp/output.txt")
        
        assert result_path == "/tmp/output.txt"
        mock_makedirs.assert_called_once()
        mock_blob_client.download_blob.assert_called_once()
    
    @patch('apps.tools.services.blob_storage.BlobStorageClient.get_blob_service_client')
    def test_delete_file_success(self, mock_get_client):
        """Test successful file deletion."""
        mock_blob_client = Mock()
        
        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        mock_get_client.return_value = mock_service_client
        
        client = BlobStorageClient()
        result = client.delete_file("uploads", "test/test.txt")
        
        assert result is True
        mock_blob_client.delete_blob.assert_called_once()
    
    @patch('apps.tools.services.blob_storage.BlobStorageClient.get_blob_service_client')
    def test_get_blob_url(self, mock_get_client):
        """Test getting blob URL."""
        mock_blob_client = Mock()
        mock_blob_client.url = "https://teststorage.blob.core.windows.net/uploads/test.txt"
        
        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        mock_get_client.return_value = mock_service_client
        
        client = BlobStorageClient()
        url = client.get_blob_url("uploads", "test/test.txt")
        
        assert url == "https://teststorage.blob.core.windows.net/uploads/test.txt"
    
    @patch('apps.tools.services.blob_storage.BlobStorageClient.get_blob_service_client')
    def test_blob_exists_returns_true(self, mock_get_client):
        """Test blob_exists returns True when blob exists."""
        mock_blob_client = Mock()
        mock_blob_client.exists.return_value = True
        
        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        mock_get_client.return_value = mock_service_client
        
        client = BlobStorageClient()
        exists = client.blob_exists("uploads", "test/test.txt")
        
        assert exists is True
        mock_blob_client.exists.assert_called_once()
    
    @patch('apps.tools.services.blob_storage.BlobStorageClient.get_blob_service_client')
    def test_blob_exists_returns_false(self, mock_get_client):
        """Test blob_exists returns False when blob doesn't exist."""
        mock_blob_client = Mock()
        mock_blob_client.exists.return_value = False
        
        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        mock_get_client.return_value = mock_service_client
        
        client = BlobStorageClient()
        exists = client.blob_exists("uploads", "test/test.txt")
        
        assert exists is False
    
    @patch('apps.tools.services.blob_storage.BlobStorageClient.get_blob_service_client')
    def test_upload_file_handles_exceptions(self, mock_get_client):
        """Test that upload_file handles exceptions properly."""
        mock_service_client = Mock()
        mock_service_client.get_blob_client.side_effect = Exception("Azure error")
        mock_get_client.return_value = mock_service_client
        
        client = BlobStorageClient()
        
        with pytest.raises(Exception, match="Azure error"):
            client.upload_file("uploads", "test/test.txt", "/tmp/test.txt")
    
    @patch('apps.tools.services.blob_storage.BlobStorageClient.get_blob_service_client')
    def test_blob_exists_handles_exceptions(self, mock_get_client):
        """Test that blob_exists handles exceptions and returns False."""
        mock_blob_client = Mock()
        mock_blob_client.exists.side_effect = Exception("Connection error")
        
        mock_service_client = Mock()
        mock_service_client.get_blob_client.return_value = mock_blob_client
        mock_get_client.return_value = mock_service_client
        
        client = BlobStorageClient()
        exists = client.blob_exists("uploads", "test/test.txt")
        
        assert exists is False
