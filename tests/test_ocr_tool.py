"""
Tests for OCR Tool (Optical Character Recognition).
"""

import json
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.tools.models import ToolExecution
from apps.tools.plugins.ocr_tool import OCRTool
from apps.tools.registry import tool_registry

User = get_user_model()


@pytest.fixture
def ocr_tool():
    """Get OCR tool instance."""
    return OCRTool()


@pytest.fixture
def sample_image():
    """Create a sample image file."""
    # Simple 1x1 pixel PNG
    png_data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
        b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    return SimpleUploadedFile(
        name="test_image.png",
        content=png_data,
        content_type="image/png",
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


class TestOCRTool:
    """Test suite for OCR tool."""

    def test_tool_registration(self):
        """Test that OCR tool is registered."""
        assert tool_registry.is_registered("ocr-tool")
        tool_instance = tool_registry.get_tool_instance("ocr-tool")
        assert tool_instance is not None
        assert isinstance(tool_instance, OCRTool)

    def test_tool_metadata(self, ocr_tool):
        """Test tool metadata."""
        metadata = ocr_tool.get_metadata()

        assert metadata["name"] == "ocr-tool"
        assert metadata["displayName"] == "OCR Text Extractor"
        assert metadata["category"] == "image"
        assert metadata["version"] == "1.0.0"
        assert "OCR" in metadata["description"]
        assert "languages" in metadata
        assert len(metadata["languages"]) == 14
        assert "eng" in metadata["languages"]
        assert "fra" in metadata["languages"]
        assert metadata["isAsync"] is True

    def test_validate_valid_image(self, ocr_tool, sample_image):
        """Test validation with valid image."""
        parameters = {"language": "eng", "ocr_mode": "3"}
        is_valid, error_msg = ocr_tool.validate(sample_image, parameters)
        assert is_valid is True
        assert error_msg is None

    def test_validate_no_file(self, ocr_tool):
        """Test validation fails without file."""
        parameters = {"language": "eng"}
        is_valid, error_msg = ocr_tool.validate(None, parameters)
        assert is_valid is False
        assert "no image file" in error_msg.lower()

    def test_validate_file_too_large(self, ocr_tool):
        """Test validation fails with file too large."""
        large_file = Mock()
        large_file.name = "large_image.png"
        large_file.size = 51 * 1024 * 1024  # 51MB

        parameters = {"language": "eng"}
        is_valid, error_msg = ocr_tool.validate(large_file, parameters)
        assert is_valid is False
        assert "exceeds maximum" in error_msg.lower()

    def test_validate_invalid_file_type(self, ocr_tool):
        """Test validation fails with unsupported file type."""
        invalid_file = SimpleUploadedFile(
            name="test.txt",
            content=b"not an image",
            content_type="text/plain",
        )

        parameters = {"language": "eng"}
        is_valid, error_msg = ocr_tool.validate(invalid_file, parameters)
        assert is_valid is False
        assert "not supported" in error_msg.lower()

    def test_validate_invalid_language(self, ocr_tool, sample_image):
        """Test validation fails with invalid language."""
        parameters = {"language": "invalid_lang"}
        is_valid, error_msg = ocr_tool.validate(sample_image, parameters)
        assert is_valid is False
        assert "unsupported language" in error_msg.lower()

    def test_validate_all_supported_languages(self, ocr_tool, sample_image):
        """Test validation succeeds for all supported languages."""
        supported_languages = [
            "eng",
            "fra",
            "deu",
            "spa",
            "ita",
            "por",
            "nld",
            "rus",
            "jpn",
            "chi_sim",
            "chi_tra",
            "kor",
            "ara",
            "hin",
        ]

        for lang in supported_languages:
            parameters = {"language": lang}
            is_valid, error_msg = ocr_tool.validate(sample_image, parameters)
            assert is_valid is True, f"Language {lang} should be valid"

    def test_validate_ocr_mode(self, ocr_tool, sample_image):
        """Test validation with different OCR modes."""
        # Valid modes
        for mode in ["0", "3", "6", "11"]:
            parameters = {"language": "eng", "ocr_mode": mode}
            is_valid, error_msg = ocr_tool.validate(sample_image, parameters)
            assert is_valid is True

    def test_validate_invalid_ocr_mode(self, ocr_tool, sample_image):
        """Test validation fails with invalid OCR mode."""
        parameters = {"language": "eng", "ocr_mode": "99"}
        is_valid, error_msg = ocr_tool.validate(sample_image, parameters)
        assert is_valid is False
        assert "invalid ocr mode" in error_msg.lower()

    def test_validate_preprocessing_flag(self, ocr_tool, sample_image):
        """Test validation with preprocessing parameter."""
        parameters = {"language": "eng", "preprocessing": "true"}
        is_valid, error_msg = ocr_tool.validate(sample_image, parameters)
        assert is_valid is True

        parameters = {"language": "eng", "preprocessing": "false"}
        is_valid, error_msg = ocr_tool.validate(sample_image, parameters)
        assert is_valid is True

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    @patch("apps.tools.plugins.ocr_tool.requests.post")
    def test_process_creates_execution(self, mock_post, mock_blob_client, ocr_tool, sample_image):
        """Test that process creates ToolExecution and uploads to blob storage."""
        # Mock blob storage
        mock_container_client = MagicMock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        # Mock Azure Function trigger
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"status": "processing"}
        mock_post.return_value = mock_response

        parameters = {"language": "eng", "ocr_mode": "3", "preprocessing": "true"}

        execution_id, filename = ocr_tool.process(sample_image, parameters)

        # Verify async response
        assert execution_id is not None
        assert filename is None

        # Verify ToolExecution was created
        execution = ToolExecution.objects.get(id=execution_id)
        assert execution.tool_name == "ocr-tool"
        assert execution.status == "pending"
        assert execution.input_filename == "test_image.png"

        # Verify blob upload was called
        mock_container_client.upload_blob.assert_called_once()

        # Verify Azure Function was triggered
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "image/ocr" in call_args[0][0]

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    @patch("apps.tools.plugins.ocr_tool.requests.post")
    def test_process_blob_upload_path(self, mock_post, mock_blob_client, ocr_tool, sample_image):
        """Test that blob is uploaded to correct path."""
        mock_container_client = MagicMock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        parameters = {"language": "eng"}
        execution_id, _ = ocr_tool.process(sample_image, parameters)

        # Check blob path
        upload_call = mock_container_client.upload_blob.call_args
        blob_name = upload_call[1]["name"]
        assert blob_name.startswith("uploads/image/")
        assert blob_name.endswith(".png")
        assert str(execution_id) in blob_name

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    @patch("apps.tools.plugins.ocr_tool.requests.post")
    def test_process_azure_function_payload(
        self, mock_post, mock_blob_client, ocr_tool, sample_image
    ):
        """Test Azure Function is called with correct payload."""
        mock_container_client = MagicMock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        parameters = {"language": "fra", "ocr_mode": "6", "preprocessing": "true"}

        execution_id, _ = ocr_tool.process(sample_image, parameters)

        # Verify payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["execution_id"] == str(execution_id)
        assert payload["language"] == "fra"
        assert payload["ocr_mode"] == "6"
        assert payload["preprocessing"] is True

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    def test_process_blob_upload_failure(self, mock_blob_client, ocr_tool, sample_image):
        """Test error handling when blob upload fails."""
        mock_container_client = MagicMock()
        mock_container_client.upload_blob.side_effect = Exception("Blob upload failed")
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        parameters = {"language": "eng"}

        with pytest.raises(Exception) as exc_info:
            ocr_tool.process(sample_image, parameters)

        assert "blob upload failed" in str(exc_info.value).lower()

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    @patch("apps.tools.plugins.ocr_tool.requests.post")
    def test_process_azure_function_failure(
        self, mock_post, mock_blob_client, ocr_tool, sample_image
    ):
        """Test error handling when Azure Function trigger fails."""
        mock_container_client = MagicMock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Function failed"}
        mock_post.return_value = mock_response

        parameters = {"language": "eng"}

        with pytest.raises(Exception) as exc_info:
            ocr_tool.process(sample_image, parameters)

        assert "azure function" in str(exc_info.value).lower()


class TestOCRToolAPI:
    """Test suite for OCR Tool API endpoints."""

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    @patch("apps.tools.plugins.ocr_tool.requests.post")
    def test_ocr_endpoint(self, mock_post, mock_blob_client, authenticated_client, sample_image):
        """Test OCR extraction via API endpoint."""
        client, user = authenticated_client

        # Mock blob storage
        mock_container_client = MagicMock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        # Mock Azure Function
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"status": "processing"}
        mock_post.return_value = mock_response

        sample_image.seek(0)

        response = client.post(
            "/api/v1/tools/ocr-tool/convert/",
            {
                "file": sample_image,
                "language": "eng",
                "ocr_mode": "3",
                "preprocessing": "true",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "execution_id" in data
        assert data["status"] == "pending"

    def test_ocr_missing_file(self, authenticated_client):
        """Test API fails without file."""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/tools/ocr-tool/convert/",
            {
                "language": "eng",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ocr_invalid_language(self, authenticated_client, sample_image):
        """Test API fails with invalid language."""
        client, user = authenticated_client

        sample_image.seek(0)

        response = client.post(
            "/api/v1/tools/ocr-tool/convert/",
            {
                "file": sample_image,
                "language": "invalid_lang",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    @patch("apps.tools.plugins.ocr_tool.requests.post")
    def test_ocr_default_parameters(
        self, mock_post, mock_blob_client, authenticated_client, sample_image
    ):
        """Test OCR with default parameters."""
        client, user = authenticated_client

        mock_container_client = MagicMock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        sample_image.seek(0)

        response = client.post(
            "/api/v1/tools/ocr-tool/convert/",
            {
                "file": sample_image,
            },
            format="multipart",
        )

        # Should use defaults: language=eng, ocr_mode=3, preprocessing=true
        assert response.status_code == status.HTTP_202_ACCEPTED


class TestOCRToolIntegration:
    """Integration tests for OCR tool workflow."""

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    @patch("apps.tools.plugins.ocr_tool.requests.post")
    def test_full_ocr_workflow(self, mock_post, mock_blob_client, ocr_tool, sample_image):
        """Test complete OCR workflow from upload to completion."""
        # Setup mocks
        mock_container_client = MagicMock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"status": "processing"}
        mock_post.return_value = mock_response

        # Step 1: Upload and trigger
        parameters = {"language": "eng", "preprocessing": "true"}
        execution_id, _ = ocr_tool.process(sample_image, parameters)

        # Verify execution created
        execution = ToolExecution.objects.get(id=execution_id)
        assert execution.status == "pending"

        # Step 2: Simulate Azure Function processing
        execution.status = "processing"
        execution.save()

        # Step 3: Simulate completion
        execution.status = "completed"
        execution.output_filename = f"{execution_id}.txt"
        execution.result_data = {"extracted_text": "Test OCR result"}
        execution.save()

        # Verify final state
        execution.refresh_from_db()
        assert execution.status == "completed"
        assert execution.result_data["extracted_text"] == "Test OCR result"

    @pytest.mark.django_db
    @patch("apps.tools.plugins.ocr_tool.BlobServiceClient")
    @patch("apps.tools.plugins.ocr_tool.requests.post")
    def test_ocr_failure_workflow(self, mock_post, mock_blob_client, ocr_tool, sample_image):
        """Test OCR workflow with failure scenario."""
        mock_container_client = MagicMock()
        mock_blob_client.return_value.get_container_client.return_value = mock_container_client

        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response

        # Upload
        parameters = {"language": "eng"}
        execution_id, _ = ocr_tool.process(sample_image, parameters)

        # Simulate failure
        execution = ToolExecution.objects.get(id=execution_id)
        execution.status = "failed"
        execution.error_message = "OCR processing failed"
        execution.save()

        # Verify error state
        execution.refresh_from_db()
        assert execution.status == "failed"
        assert "failed" in execution.error_message.lower()
