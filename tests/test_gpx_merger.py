"""
Tests for GPX Merger tool.
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.tools.plugins.gpx_merger import GPXMerger
from apps.tools.registry import tool_registry

User = get_user_model()


@pytest.fixture
def gpx_merger_tool():
    """Get GPX merger tool instance."""
    return GPXMerger()


@pytest.fixture
def sample_gpx_file_1():
    """Create a sample GPX file for testing."""
    gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Track 1</name>
    <time>2024-01-01T10:00:00Z</time>
  </metadata>
  <trk>
    <name>Morning Run</name>
    <trkseg>
      <trkpt lat="45.0" lon="-122.0">
        <ele>100</ele>
        <time>2024-01-01T10:00:00Z</time>
      </trkpt>
      <trkpt lat="45.1" lon="-122.1">
        <ele>110</ele>
        <time>2024-01-01T10:05:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
    return SimpleUploadedFile(
        name="track1.gpx",
        content=gpx_content,
        content_type="application/gpx+xml",
    )


@pytest.fixture
def sample_gpx_file_2():
    """Create a second sample GPX file for testing."""
    gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Track 2</name>
    <time>2024-01-01T12:00:00Z</time>
  </metadata>
  <trk>
    <name>Afternoon Ride</name>
    <trkseg>
      <trkpt lat="45.2" lon="-122.2">
        <ele>120</ele>
        <time>2024-01-01T12:00:00Z</time>
      </trkpt>
      <trkpt lat="45.3" lon="-122.3">
        <ele>130</ele>
        <time>2024-01-01T12:10:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
    return SimpleUploadedFile(
        name="track2.gpx",
        content=gpx_content,
        content_type="application/gpx+xml",
    )


@pytest.fixture
def sample_gpx_file_3():
    """Create a third sample GPX file for testing."""
    gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Track 3</name>
    <time>2024-01-01T14:00:00Z</time>
  </metadata>
  <trk>
    <name>Evening Walk</name>
    <trkseg>
      <trkpt lat="45.4" lon="-122.4">
        <ele>140</ele>
        <time>2024-01-01T14:00:00Z</time>
      </trkpt>
      <trkpt lat="45.5" lon="-122.5">
        <ele>150</ele>
        <time>2024-01-01T14:15:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
    return SimpleUploadedFile(
        name="track3.gpx",
        content=gpx_content,
        content_type="application/gpx+xml",
    )


@pytest.fixture
def authenticated_client(db):
    """Create an authenticated API client."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


class TestGPXMergerTool:
    """Test suite for GPXMerger tool."""

    def test_tool_registration(self):
        """Test that GPX merger tool is registered."""
        assert tool_registry.is_registered("gpx-merger")
        tool_instance = tool_registry.get_tool_instance("gpx-merger")
        assert tool_instance is not None
        assert isinstance(tool_instance, GPXMerger)

    def test_tool_metadata(self, gpx_merger_tool):
        """Test tool metadata."""
        metadata = gpx_merger_tool.get_metadata()

        assert metadata["name"] == "gpx-merger"
        assert metadata["displayName"] == "GPX Merger"
        assert metadata["category"] == "file"
        assert metadata["version"] == "1.0.0"
        assert "GPX" in metadata["description"]

    def test_validate_single_file(self, gpx_merger_tool, sample_gpx_file_1):
        """Test validation of single GPX file."""
        parameters = {"merge_mode": "chronological"}
        is_valid, error_msg = gpx_merger_tool.validate(sample_gpx_file_1, parameters)
        assert is_valid is True
        assert error_msg is None

    def test_validate_invalid_file_type(self, gpx_merger_tool):
        """Test validation fails with non-GPX file."""
        invalid_file = SimpleUploadedFile(
            name="test.txt",
            content=b"not a gpx file",
            content_type="text/plain",
        )
        parameters = {"merge_mode": "chronological"}
        is_valid, error_msg = gpx_merger_tool.validate(invalid_file, parameters)
        assert is_valid is False
        assert "not supported" in error_msg.lower()

    def test_validate_file_too_large(self, gpx_merger_tool):
        """Test validation fails when file is too large."""
        large_file = MagicMock()
        large_file.name = "large_track.gpx"
        large_file.size = 60 * 1024 * 1024  # 60 MB (exceeds 50 MB limit)

        parameters = {"merge_mode": "chronological"}
        is_valid, error_msg = gpx_merger_tool.validate(large_file, parameters)
        assert is_valid is False
        assert "exceeds maximum" in error_msg.lower()

    def test_validate_multiple_files_success(
        self, gpx_merger_tool, sample_gpx_file_1, sample_gpx_file_2
    ):
        """Test validation of multiple files succeeds."""
        files = [sample_gpx_file_1, sample_gpx_file_2]
        parameters = {"merge_mode": "chronological"}
        is_valid, error_msg = gpx_merger_tool.validate_multiple(files, parameters)
        assert is_valid is True
        assert error_msg is None

    def test_validate_multiple_files_too_few(self, gpx_merger_tool, sample_gpx_file_1):
        """Test validation fails with only one file."""
        files = [sample_gpx_file_1]
        parameters = {"merge_mode": "chronological"}
        is_valid, error_msg = gpx_merger_tool.validate_multiple(files, parameters)
        assert is_valid is False
        assert "at least 2 files" in error_msg.lower()

    def test_validate_multiple_files_too_many(self, gpx_merger_tool, sample_gpx_file_1):
        """Test validation fails with too many files."""
        # Create 21 files (exceeds limit of 20)
        files = [sample_gpx_file_1] * 21
        parameters = {"merge_mode": "chronological"}
        is_valid, error_msg = gpx_merger_tool.validate_multiple(files, parameters)
        assert is_valid is False
        assert "maximum 20 files" in error_msg.lower()

    def test_validate_multiple_invalid_merge_mode(
        self, gpx_merger_tool, sample_gpx_file_1, sample_gpx_file_2
    ):
        """Test validation fails with invalid merge mode."""
        files = [sample_gpx_file_1, sample_gpx_file_2]
        parameters = {"merge_mode": "invalid_mode"}
        is_valid, error_msg = gpx_merger_tool.validate_multiple(files, parameters)
        assert is_valid is False
        assert "invalid merge_mode" in error_msg.lower()

    def test_process_single_file_raises_error(self, gpx_merger_tool, sample_gpx_file_1):
        """Test that processing single file raises error."""
        parameters = {"merge_mode": "chronological"}
        with pytest.raises(Exception) as exc_info:
            gpx_merger_tool.process(sample_gpx_file_1, parameters)
        assert "multiple files" in str(exc_info.value).lower()

    @patch("apps.tools.plugins.gpx_merger.BlobServiceClient")
    @patch("requests.post")
    def test_process_multiple_files(
        self,
        mock_requests_post,
        mock_blob_service,
        gpx_merger_tool,
        sample_gpx_file_1,
        sample_gpx_file_2,
        sample_gpx_file_3,
    ):
        """Test processing multiple GPX files for merging."""
        # Mock blob storage client
        mock_blob_client = MagicMock()
        mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client

        # Mock HTTP trigger response
        mock_requests_post.return_value = MagicMock(status_code=200)

        files = [sample_gpx_file_1, sample_gpx_file_2, sample_gpx_file_3]
        parameters = {
            "merge_mode": "chronological",
            "output_name": "my_merged_track",
        }

        # Mock settings
        with patch("django.conf.settings") as mock_settings:
            mock_settings.AZURE_STORAGE_CONNECTION_STRING = "UseDevelopmentStorage=true"
            mock_settings.AZURE_FUNCTION_BASE_URL = "http://localhost:7071"

            results = gpx_merger_tool.process_multiple(files, parameters)

            # Should return single result tuple
            assert len(results) == 1
            execution_id, output_filename = results[0]

            # Verify execution ID is UUID
            assert len(execution_id) == 36  # UUID format
            assert output_filename == "my_merged_track.gpx"

            # Verify blob uploads (3 files)
            assert mock_blob_client.upload_blob.call_count == 3

            # Verify HTTP trigger was called
            assert mock_requests_post.called

    @patch("apps.tools.plugins.gpx_merger.BlobServiceClient")
    def test_process_multiple_preserves_file_order(
        self,
        mock_blob_service,
        gpx_merger_tool,
        sample_gpx_file_1,
        sample_gpx_file_2,
    ):
        """Test that file upload preserves order with sequential naming."""
        # Mock blob storage
        mock_blob_client = MagicMock()
        mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client

        files = [sample_gpx_file_1, sample_gpx_file_2]
        parameters = {"merge_mode": "sequential", "output_name": "test_merge"}

        with patch("django.conf.settings") as mock_settings:
            mock_settings.AZURE_STORAGE_CONNECTION_STRING = "UseDevelopmentStorage=true"
            mock_settings.AZURE_FUNCTION_BASE_URL = "http://localhost:7071"

            with patch("requests.post"):
                gpx_merger_tool.process_multiple(files, parameters)

                # Verify blob names include sequential indices
                calls = mock_blob_service.return_value.get_blob_client.call_args_list
                blob_names = [call[1]["blob"] for call in calls]

                # Should have _000, _001 suffixes
                assert any("_000.gpx" in name for name in blob_names)
                assert any("_001.gpx" in name for name in blob_names)


class TestGPXMergerAPI:
    """Test suite for GPX Merger API endpoints."""

    @patch("apps.tools.plugins.gpx_merger.BlobServiceClient")
    @patch("requests.post")
    def test_merge_endpoint(
        self,
        mock_requests_post,
        mock_blob_service,
        authenticated_client,
        sample_gpx_file_1,
        sample_gpx_file_2,
    ):
        """Test merge API endpoint."""
        client, user = authenticated_client

        # Mock blob storage
        mock_blob_client = MagicMock()
        mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client
        mock_requests_post.return_value = MagicMock(status_code=200)

        # Reset file pointers
        sample_gpx_file_1.seek(0)
        sample_gpx_file_2.seek(0)

        with patch("django.conf.settings") as mock_settings:
            mock_settings.AZURE_STORAGE_CONNECTION_STRING = "UseDevelopmentStorage=true"
            mock_settings.AZURE_FUNCTION_BASE_URL = "http://localhost:7071"

            response = client.post(
                "/api/v1/tools/gpx-merger/merge/",
                {
                    "files[]": [sample_gpx_file_1, sample_gpx_file_2],
                    "merge_mode": "chronological",
                    "output_name": "test_merged",
                },
                format="multipart",
            )

            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()

            assert "executions" in data
            assert len(data["executions"]) == 1

            execution = data["executions"][0]
            assert "executionId" in execution
            assert execution["status"] == "pending"
            assert "statusUrl" in execution

    def test_merge_endpoint_missing_files(self, authenticated_client):
        """Test merge endpoint fails without files."""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/tools/gpx-merger/merge/",
            {
                "merge_mode": "chronological",
                "output_name": "test_merged",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert "no files" in data["error"].lower()

    @patch("apps.tools.plugins.gpx_merger.BlobServiceClient")
    def test_merge_endpoint_too_few_files(
        self, mock_blob_service, authenticated_client, sample_gpx_file_1
    ):
        """Test merge endpoint fails with only one file."""
        client, user = authenticated_client

        sample_gpx_file_1.seek(0)

        response = client.post(
            "/api/v1/tools/gpx-merger/merge/",
            {
                "files[]": [sample_gpx_file_1],
                "merge_mode": "chronological",
                "output_name": "test_merged",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert "at least 2 files" in data["error"].lower()
