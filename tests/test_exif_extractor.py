"""
Tests for EXIF Metadata Extractor tool.
"""

import io
import json
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from PIL.ExifTags import TAGS

from apps.tools.plugins.exif_extractor import EXIFExtractor
from apps.tools.registry import tool_registry

User = get_user_model()


@pytest.fixture
def exif_tool():
    """Get EXIF extractor tool instance."""
    return EXIFExtractor()


@pytest.fixture
def sample_image_with_exif():
    """Create a sample image with EXIF data."""
    # Create a simple image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Add EXIF data
    exif_dict = {
        271: "Test Camera Make",  # Make
        272: "Test Camera Model",  # Model
        306: "2024:12:14 10:30:00",  # DateTime
    }
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG', exif=b'')  # Basic JPEG
    img_bytes.seek(0)
    
    return SimpleUploadedFile(
        name="test_image.jpg",
        content=img_bytes.read(),
        content_type="image/jpeg",
    )


@pytest.fixture
def sample_image_no_exif():
    """Create a sample image without EXIF data."""
    img = Image.new('RGB', (50, 50), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return SimpleUploadedFile(
        name="no_exif.png",
        content=img_bytes.read(),
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


class TestEXIFExtractorTool:
    """Test suite for EXIFExtractor tool."""

    def test_tool_registration(self):
        """Test that EXIF extractor tool is registered."""
        assert tool_registry.is_registered("exif-extractor")
        tool_instance = tool_registry.get_tool_instance("exif-extractor")
        assert tool_instance is not None
        assert isinstance(tool_instance, EXIFExtractor)

    def test_tool_metadata(self, exif_tool):
        """Test tool metadata."""
        metadata = exif_tool.get_metadata()

        assert metadata["name"] == "exif-extractor"
        assert metadata["displayName"] == "EXIF Metadata Extractor"
        assert metadata["category"] == "image"
        assert metadata["version"] == "1.0.0"
        assert "EXIF" in metadata["description"]
        assert "export_formats" in metadata
        assert "json" in metadata["export_formats"]
        assert "csv" in metadata["export_formats"]

    def test_validate_valid_image(self, exif_tool, sample_image_with_exif):
        """Test validation with valid image."""
        is_valid, error_msg = exif_tool.validate(sample_image_with_exif, {})
        assert is_valid is True
        assert error_msg is None

    def test_validate_no_file(self, exif_tool):
        """Test validation fails without file."""
        is_valid, error_msg = exif_tool.validate(None, {})
        assert is_valid is False
        assert "no image file" in error_msg.lower()

    def test_validate_file_too_large(self, exif_tool):
        """Test validation fails with file too large."""
        from unittest.mock import MagicMock
        
        large_file = MagicMock()
        large_file.name = "large_image.jpg"
        large_file.size = 21 * 1024 * 1024  # 21MB
        
        is_valid, error_msg = exif_tool.validate(large_file, {})
        assert is_valid is False
        assert "exceeds maximum" in error_msg.lower()

    def test_validate_invalid_file_type(self, exif_tool):
        """Test validation fails with unsupported file type."""
        invalid_file = SimpleUploadedFile(
            name="test.txt",
            content=b"not an image",
            content_type="text/plain",
        )
        
        is_valid, error_msg = exif_tool.validate(invalid_file, {})
        assert is_valid is False
        assert "not supported" in error_msg.lower()

    def test_validate_corrupted_image(self, exif_tool):
        """Test validation fails with corrupted image."""
        corrupted_file = SimpleUploadedFile(
            name="corrupted.jpg",
            content=b"corrupted image data",
            content_type="image/jpeg",
        )
        
        is_valid, error_msg = exif_tool.validate(corrupted_file, {})
        assert is_valid is False
        assert "invalid" in error_msg.lower()

    def test_validate_export_format(self, exif_tool, sample_image_with_exif):
        """Test validation with export format parameter."""
        parameters = {"export_format": "json"}
        is_valid, error_msg = exif_tool.validate(sample_image_with_exif, parameters)
        assert is_valid is True
        
        parameters = {"export_format": "csv"}
        is_valid, error_msg = exif_tool.validate(sample_image_with_exif, parameters)
        assert is_valid is True

    def test_validate_invalid_export_format(self, exif_tool, sample_image_with_exif):
        """Test validation fails with invalid export format."""
        parameters = {"export_format": "xml"}
        is_valid, error_msg = exif_tool.validate(sample_image_with_exif, parameters)
        assert is_valid is False
        assert "invalid export format" in error_msg.lower()

    def test_process_image_basic(self, exif_tool, sample_image_with_exif):
        """Test processing image and extracting basic info."""
        result, filename = exif_tool.process(sample_image_with_exif, {})
        
        assert filename is None  # Synchronous tool
        assert isinstance(result, dict)
        assert "image_info" in result
        assert "exif_data" in result
        assert "has_exif" in result
        
        # Check image info
        assert result["image_info"]["Filename"] == "test_image.jpg"
        assert result["image_info"]["Format"] == "JPEG"
        assert result["image_info"]["Width"] == 100
        assert result["image_info"]["Height"] == 100

    def test_process_image_no_exif(self, exif_tool, sample_image_no_exif):
        """Test processing image without EXIF data."""
        result, filename = exif_tool.process(sample_image_no_exif, {})
        
        assert result["has_exif"] is False
        assert result["exif_data"] is None or len(result["exif_data"]) == 0
        assert result["has_gps"] is False

    def test_process_with_json_export(self, exif_tool, sample_image_with_exif):
        """Test processing with JSON export."""
        parameters = {"export_format": "json"}
        result, filename = exif_tool.process(sample_image_with_exif, parameters)
        
        assert "export_data" in result
        assert result["export_format"] == "json"
        
        # Verify it's valid JSON
        export_data = result["export_data"]
        parsed = json.loads(export_data)
        assert "image_info" in parsed
        assert "exif_data" in parsed
        assert "gps_data" in parsed

    def test_process_with_csv_export(self, exif_tool, sample_image_with_exif):
        """Test processing with CSV export."""
        parameters = {"export_format": "csv"}
        result, filename = exif_tool.process(sample_image_with_exif, parameters)
        
        assert "export_data" in result
        assert result["export_format"] == "csv"
        
        # Verify CSV structure
        export_data = result["export_data"]
        lines = export_data.strip().split('\n')
        assert len(lines) > 0
        assert "Category,Tag,Value" in lines[0]

    def test_convert_to_degrees(self, exif_tool):
        """Test GPS coordinate conversion."""
        # 48°51'30.4"N = 48.8584°
        coords = ((48, 1), (51, 1), (30.4, 1))
        degrees = exif_tool._convert_to_degrees(coords)
        assert abs(degrees - 48.8584) < 0.001

    def test_format_exif_value_bytes(self, exif_tool):
        """Test formatting EXIF value from bytes."""
        byte_value = b"Test Value"
        formatted = exif_tool._format_exif_value(byte_value)
        assert formatted == "Test Value"

    def test_format_exif_value_tuple(self, exif_tool):
        """Test formatting EXIF value from tuple."""
        tuple_value = (1, 2, 3)
        formatted = exif_tool._format_exif_value(tuple_value)
        assert formatted == "1, 2, 3"

    def test_format_exif_value_string(self, exif_tool):
        """Test formatting EXIF value from string."""
        string_value = "Test String"
        formatted = exif_tool._format_exif_value(string_value)
        assert formatted == "Test String"


class TestEXIFExtractorAPI:
    """Test suite for EXIF Extractor API endpoints."""

    def test_extract_endpoint(self, authenticated_client, sample_image_with_exif):
        """Test extraction via API endpoint."""
        client, user = authenticated_client

        sample_image_with_exif.seek(0)
        
        response = client.post(
            "/api/v1/tools/exif-extractor/convert/",
            {
                "file": sample_image_with_exif,
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "image_info" in data
        assert "exif_data" in data
        assert data["image_info"]["Filename"] == "test_image.jpg"

    def test_extract_with_json_export(self, authenticated_client, sample_image_with_exif):
        """Test extraction with JSON export via API."""
        client, user = authenticated_client

        sample_image_with_exif.seek(0)
        
        response = client.post(
            "/api/v1/tools/exif-extractor/convert/",
            {
                "file": sample_image_with_exif,
                "export_format": "json",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "export_data" in data
        assert data["export_format"] == "json"

    def test_extract_with_csv_export(self, authenticated_client, sample_image_with_exif):
        """Test extraction with CSV export via API."""
        client, user = authenticated_client

        sample_image_with_exif.seek(0)
        
        response = client.post(
            "/api/v1/tools/exif-extractor/convert/",
            {
                "file": sample_image_with_exif,
                "export_format": "csv",
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "export_data" in data
        assert data["export_format"] == "csv"

    def test_missing_file(self, authenticated_client):
        """Test API fails without file."""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/tools/exif-extractor/convert/",
            {},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
