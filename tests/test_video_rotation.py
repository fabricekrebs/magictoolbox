"""
Tests for video rotation tool.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.tools.plugins.video_rotation import VideoRotation
from apps.tools.registry import tool_registry

User = get_user_model()


@pytest.fixture
def video_rotation_tool():
    """Get video rotation tool instance."""
    return VideoRotation()


@pytest.fixture
def sample_video_file():
    """Create a sample video file for testing."""
    # Create a minimal video file for testing (just a placeholder)
    video_content = b"RIFF" + b"\x00" * 100  # Minimal AVI file header
    return SimpleUploadedFile(
        name="test_video.mp4",
        content=video_content,
        content_type="video/mp4",
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


class TestVideoRotationTool:
    """Test suite for VideoRotation tool."""

    def test_tool_registration(self):
        """Test that video rotation tool is registered."""
        assert tool_registry.is_registered("video-rotation")
        tool_instance = tool_registry.get_tool_instance("video-rotation")
        assert tool_instance is not None
        assert isinstance(tool_instance, VideoRotation)

    def test_tool_metadata(self, video_rotation_tool):
        """Test tool metadata."""
        metadata = video_rotation_tool.get_metadata()

        assert metadata["name"] == "video-rotation"
        assert metadata["displayName"] == "Video Rotation"
        assert metadata["category"] == "video"
        assert "rotationOptions" in metadata
        assert len(metadata["rotationOptions"]) == 3

        # Check rotation options
        rotation_values = [opt["value"] for opt in metadata["rotationOptions"]]
        assert "90_cw" in rotation_values
        assert "90_ccw" in rotation_values
        assert "180" in rotation_values

    def test_validate_valid_file(self, video_rotation_tool, sample_video_file):
        """Test validation with valid file and parameters."""
        parameters = {"rotation": "90_cw"}
        is_valid, error_msg = video_rotation_tool.validate(sample_video_file, parameters)
        assert is_valid is True
        assert error_msg is None

    def test_validate_missing_rotation(self, video_rotation_tool, sample_video_file):
        """Test validation fails when rotation parameter is missing."""
        parameters = {}
        is_valid, error_msg = video_rotation_tool.validate(sample_video_file, parameters)
        assert is_valid is False
        assert "rotation" in error_msg.lower()

    def test_validate_invalid_rotation(self, video_rotation_tool, sample_video_file):
        """Test validation fails with invalid rotation angle."""
        parameters = {"rotation": "invalid"}
        is_valid, error_msg = video_rotation_tool.validate(sample_video_file, parameters)
        assert is_valid is False
        assert "invalid rotation" in error_msg.lower()

    def test_validate_file_too_large(self, video_rotation_tool):
        """Test validation fails when file is too large."""
        # Create a mock file that's too large
        large_file = MagicMock()
        large_file.name = "large_video.mp4"
        large_file.size = 600 * 1024 * 1024  # 600 MB (exceeds 500 MB limit)

        parameters = {"rotation": "90_cw"}
        is_valid, error_msg = video_rotation_tool.validate(large_file, parameters)
        assert is_valid is False
        assert "exceeds maximum" in error_msg.lower()

    def test_validate_unsupported_format(self, video_rotation_tool):
        """Test validation fails with unsupported file format."""
        unsupported_file = SimpleUploadedFile(
            name="test_file.txt",
            content=b"not a video",
            content_type="text/plain",
        )

        parameters = {"rotation": "90_cw"}
        is_valid, error_msg = video_rotation_tool.validate(unsupported_file, parameters)
        assert is_valid is False
        assert "unsupported file type" in error_msg.lower()

    @patch("subprocess.run")
    def test_process_90_clockwise(self, mock_run, video_rotation_tool, sample_video_file):
        """Test video rotation 90 degrees clockwise."""
        # Mock successful FFmpeg execution
        mock_run.return_value = MagicMock(returncode=0, stderr=b"")

        # Create a temp output file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
            temp_output.write(b"rotated video content")
            temp_output_path = temp_output.name

        # Mock the tempfile creation to return our test file
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = temp_output_path

            parameters = {"rotation": "90_cw"}
            try:
                output_path, output_filename = video_rotation_tool.process(
                    sample_video_file, parameters
                )

                assert output_filename.endswith("_rotated_90_cw.mp4")
                assert mock_run.called

                # Verify FFmpeg command
                call_args = mock_run.call_args[0][0]
                assert "ffmpeg" in call_args
                assert "transpose=1" in " ".join(call_args)

            finally:
                # Cleanup
                if os.path.exists(temp_output_path):
                    os.unlink(temp_output_path)

    @patch("subprocess.run")
    def test_process_90_counterclockwise(self, mock_run, video_rotation_tool, sample_video_file):
        """Test video rotation 90 degrees counter-clockwise."""
        mock_run.return_value = MagicMock(returncode=0, stderr=b"")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
            temp_output.write(b"rotated video content")
            temp_output_path = temp_output.name

        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = temp_output_path

            parameters = {"rotation": "90_ccw"}
            try:
                output_path, output_filename = video_rotation_tool.process(
                    sample_video_file, parameters
                )

                assert output_filename.endswith("_rotated_90_ccw.mp4")
                assert mock_run.called

                # Verify FFmpeg command
                call_args = mock_run.call_args[0][0]
                assert "transpose=2" in " ".join(call_args)

            finally:
                if os.path.exists(temp_output_path):
                    os.unlink(temp_output_path)

    @patch("subprocess.run")
    def test_process_180(self, mock_run, video_rotation_tool, sample_video_file):
        """Test video rotation 180 degrees."""
        mock_run.return_value = MagicMock(returncode=0, stderr=b"")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
            temp_output.write(b"rotated video content")
            temp_output_path = temp_output.name

        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_temp.return_value.__enter__.return_value.name = temp_output_path

            parameters = {"rotation": "180"}
            try:
                output_path, output_filename = video_rotation_tool.process(
                    sample_video_file, parameters
                )

                assert output_filename.endswith("_rotated_180.mp4")
                assert mock_run.called

                # Verify FFmpeg command (180 = transpose twice)
                call_args = mock_run.call_args[0][0]
                assert "transpose=2,transpose=2" in " ".join(call_args)

            finally:
                if os.path.exists(temp_output_path):
                    os.unlink(temp_output_path)

    @patch("subprocess.run")
    def test_process_ffmpeg_failure(self, mock_run, video_rotation_tool, sample_video_file):
        """Test handling of FFmpeg failure."""
        # Mock FFmpeg failure
        mock_run.return_value = MagicMock(returncode=1, stderr=b"FFmpeg error: Invalid input")

        parameters = {"rotation": "90_cw"}

        from apps.core.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError) as exc_info:
            video_rotation_tool.process(sample_video_file, parameters)

        assert "video rotation failed" in str(exc_info.value).lower()

    def test_cleanup(self, video_rotation_tool):
        """Test cleanup of temporary files."""
        # Create temporary test files
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(b"test content")
                temp_files.append(temp_file.name)

        # Verify files exist
        for file_path in temp_files:
            assert os.path.exists(file_path)

        # Cleanup
        video_rotation_tool.cleanup(*temp_files)

        # Verify files are deleted
        for file_path in temp_files:
            assert not os.path.exists(file_path)


class TestVideoRotationAPI:
    """Test suite for Video Rotation API endpoints."""

    def test_list_tools_includes_video_rotation(self, authenticated_client):
        """Test that video rotation tool appears in tools list."""
        client, user = authenticated_client

        response = client.get("/api/v1/tools/")
        assert response.status_code == status.HTTP_200_OK

        tools = response.json()
        video_rotation_tool = next((t for t in tools if t["name"] == "video-rotation"), None)
        assert video_rotation_tool is not None
        assert video_rotation_tool["displayName"] == "Video Rotation"

    def test_get_tool_metadata(self, authenticated_client):
        """Test getting video rotation tool metadata."""
        client, user = authenticated_client

        response = client.get("/api/v1/tools/video-rotation/")
        assert response.status_code == status.HTTP_200_OK

        metadata = response.json()
        assert metadata["name"] == "video-rotation"
        assert "rotationOptions" in metadata

    @patch("subprocess.run")
    def test_convert_video_api(self, mock_run, authenticated_client, sample_video_file):
        """Test video conversion via API."""
        client, user = authenticated_client

        # Mock successful FFmpeg execution
        mock_run.return_value = MagicMock(returncode=0, stderr=b"")

        # Create a temp output file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
            temp_output.write(b"rotated video content")
            temp_output_path = temp_output.name

        try:
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = temp_output_path

                response = client.post(
                    "/api/v1/tools/video-rotation/convert/",
                    {"file": sample_video_file, "rotation": "90_cw"},
                    format="multipart",
                )

                assert response.status_code == status.HTTP_200_OK
                assert response["Content-Type"] == "video/mp4"
                assert "attachment" in response["Content-Disposition"]

        finally:
            if os.path.exists(temp_output_path):
                os.unlink(temp_output_path)

    def test_convert_video_missing_rotation(self, authenticated_client, sample_video_file):
        """Test API returns error when rotation parameter is missing."""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/tools/video-rotation/convert/",
            {"file": sample_video_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rotation" in response.json()["error"].lower()

    def test_convert_video_requires_authentication(self, sample_video_file):
        """Test that video conversion requires authentication."""
        client = APIClient()

        response = client.post(
            "/api/v1/tools/video-rotation/convert/",
            {"file": sample_video_file, "rotation": "90_cw"},
            format="multipart",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
