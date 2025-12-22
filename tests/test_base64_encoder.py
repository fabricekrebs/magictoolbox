"""
Tests for Base64 Encoder/Decoder tool.
"""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.tools.plugins.base64_encoder import Base64Encoder
from apps.tools.registry import tool_registry

User = get_user_model()


@pytest.fixture
def base64_tool():
    """Get Base64 encoder tool instance."""
    return Base64Encoder()


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


class TestBase64EncoderTool:
    """Test suite for Base64Encoder tool."""

    def test_tool_registration(self):
        """Test that Base64 encoder tool is registered."""
        assert tool_registry.is_registered("base64-encoder")
        tool_instance = tool_registry.get_tool_instance("base64-encoder")
        assert tool_instance is not None
        assert isinstance(tool_instance, Base64Encoder)

    def test_tool_metadata(self, base64_tool):
        """Test tool metadata."""
        metadata = base64_tool.get_metadata()

        assert metadata["name"] == "base64-encoder"
        assert metadata["displayName"] == "Base64 Encoder/Decoder"
        assert metadata["category"] == "conversion"
        assert metadata["version"] == "1.0.0"
        assert "Base64" in metadata["description"]
        assert "modes" in metadata
        assert "encode" in metadata["modes"]
        assert "decode" in metadata["modes"]

    def test_validate_encode_with_text(self, base64_tool):
        """Test validation for encoding text."""
        parameters = {"mode": "encode", "text": "Hello World"}
        is_valid, error_msg = base64_tool.validate(None, parameters)
        assert is_valid is True
        assert error_msg is None

    def test_validate_decode_with_text(self, base64_tool):
        """Test validation for decoding text."""
        parameters = {"mode": "decode", "text": "SGVsbG8gV29ybGQ="}
        is_valid, error_msg = base64_tool.validate(None, parameters)
        assert is_valid is True
        assert error_msg is None

    def test_validate_invalid_mode(self, base64_tool):
        """Test validation fails with invalid mode."""
        parameters = {"mode": "invalid", "text": "test"}
        is_valid, error_msg = base64_tool.validate(None, parameters)
        assert is_valid is False
        assert "invalid mode" in error_msg.lower()

    def test_validate_no_text_or_file(self, base64_tool):
        """Test validation fails without text or file."""
        parameters = {"mode": "encode"}
        is_valid, error_msg = base64_tool.validate(None, parameters)
        assert is_valid is False
        assert "no text input or file" in error_msg.lower()

    def test_validate_text_too_large(self, base64_tool):
        """Test validation fails when text exceeds size limit."""
        large_text = "A" * (11 * 1024 * 1024)  # 11MB
        parameters = {"mode": "encode", "text": large_text}
        is_valid, error_msg = base64_tool.validate(None, parameters)
        assert is_valid is False
        assert "exceeds maximum" in error_msg.lower()

    def test_validate_file_upload(self, base64_tool):
        """Test validation with file upload."""
        test_file = SimpleUploadedFile(
            name="test.txt",
            content=b"Hello World",
            content_type="text/plain",
        )
        parameters = {"mode": "encode"}
        is_valid, error_msg = base64_tool.validate(test_file, parameters)
        assert is_valid is True
        assert error_msg is None

    def test_validate_file_too_large(self, base64_tool):
        """Test validation fails with file too large."""
        from unittest.mock import MagicMock

        large_file = MagicMock()
        large_file.name = "large.txt"
        large_file.size = 11 * 1024 * 1024  # 11MB

        parameters = {"mode": "encode"}
        is_valid, error_msg = base64_tool.validate(large_file, parameters)
        assert is_valid is False
        assert "exceeds maximum" in error_msg.lower()

    def test_validate_invalid_base64_format(self, base64_tool):
        """Test validation fails with invalid base64 format."""
        parameters = {"mode": "decode", "text": "Hello World!@#$%"}
        is_valid, error_msg = base64_tool.validate(None, parameters)
        assert is_valid is False
        assert "invalid" in error_msg.lower()

    def test_process_encode_text(self, base64_tool):
        """Test encoding plain text to Base64."""
        parameters = {"mode": "encode", "text": "Hello World"}
        result, filename = base64_tool.process(None, parameters)

        assert filename is None  # Synchronous tool
        assert isinstance(result, dict)
        assert result["result"] == "SGVsbG8gV29ybGQ="
        assert result["mode"] == "encode"
        assert result["operation"] == "encoded"
        assert result["input_length"] == 11
        assert result["output_length"] == 16

    def test_process_decode_text(self, base64_tool):
        """Test decoding Base64 to plain text."""
        parameters = {"mode": "decode", "text": "SGVsbG8gV29ybGQ="}
        result, filename = base64_tool.process(None, parameters)

        assert filename is None
        assert isinstance(result, dict)
        assert result["result"] == "Hello World"
        assert result["mode"] == "decode"
        assert result["operation"] == "decoded"
        assert result["input_length"] == 16
        assert result["output_length"] == 11

    def test_process_encode_file(self, base64_tool):
        """Test encoding from uploaded file."""
        test_file = SimpleUploadedFile(
            name="test.txt",
            content=b"Test content",
            content_type="text/plain",
        )
        parameters = {"mode": "encode"}
        result, filename = base64_tool.process(test_file, parameters)

        assert result["result"] == "VGVzdCBjb250ZW50"
        assert result["operation"] == "encoded"

    def test_process_decode_file(self, base64_tool):
        """Test decoding from uploaded file."""
        test_file = SimpleUploadedFile(
            name="encoded.txt",
            content=b"VGVzdCBjb250ZW50",
            content_type="text/plain",
        )
        parameters = {"mode": "decode"}
        result, filename = base64_tool.process(test_file, parameters)

        assert result["result"] == "Test content"
        assert result["operation"] == "decoded"

    def test_process_invalid_base64_decode(self, base64_tool):
        """Test error handling for invalid Base64 during decode."""
        parameters = {"mode": "decode", "text": "NotValidBase64!!!"}

        with pytest.raises(Exception) as exc_info:
            base64_tool.process(None, parameters)

        assert "invalid" in str(exc_info.value).lower()

    def test_process_unicode_text(self, base64_tool):
        """Test encoding/decoding Unicode text."""
        unicode_text = "Hello 世界 🌍"
        parameters = {"mode": "encode", "text": unicode_text}
        result, _ = base64_tool.process(None, parameters)

        encoded = result["result"]

        # Now decode it back
        decode_params = {"mode": "decode", "text": encoded}
        decode_result, _ = base64_tool.process(None, decode_params)

        assert decode_result["result"] == unicode_text

    def test_process_multiline_text(self, base64_tool):
        """Test encoding/decoding multiline text."""
        multiline = "Line 1\nLine 2\nLine 3"
        parameters = {"mode": "encode", "text": multiline}
        result, _ = base64_tool.process(None, parameters)

        # Decode back
        decode_params = {"mode": "decode", "text": result["result"]}
        decode_result, _ = base64_tool.process(None, decode_params)

        assert decode_result["result"] == multiline


class TestBase64EncoderAPI:
    """Test suite for Base64 Encoder API endpoints."""

    def test_encode_endpoint(self, authenticated_client):
        """Test encoding via API endpoint."""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/tools/base64-encoder/convert/",
            {"mode": "encode", "text": "Hello World"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"] == "SGVsbG8gV29ybGQ="
        assert data["mode"] == "encode"

    def test_decode_endpoint(self, authenticated_client):
        """Test decoding via API endpoint."""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/tools/base64-encoder/convert/",
            {"mode": "decode", "text": "SGVsbG8gV29ybGQ="},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"] == "Hello World"
        assert data["mode"] == "decode"

    def test_missing_mode(self, authenticated_client):
        """Test API fails without mode parameter."""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/tools/base64-encoder/convert/",
            {"text": "Hello World"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_mode(self, authenticated_client):
        """Test API fails with invalid mode."""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/tools/base64-encoder/convert/",
            {"mode": "invalid", "text": "Hello World"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
