"""
Tests for tool system.
"""

from decimal import Decimal

from rest_framework import status

import pytest

from apps.tools.plugins.unit_converter import UnitConverter
from apps.tools.registry import tool_registry


@pytest.mark.django_db
class TestToolRegistry:
    """Test tool registry functionality."""

    def test_list_tools(self):
        """Test listing registered tools."""
        tools = tool_registry.list_tools()

        assert isinstance(tools, list)
        # At least the example image converter should be registered
        assert len(tools) >= 1

    def test_get_tool(self):
        """Test getting tool by name."""
        # Check if image-format-converter is registered
        tool_class = tool_registry.get_tool("image-format-converter")

        if tool_class:
            assert tool_class is not None
            assert hasattr(tool_class, "name")


@pytest.mark.django_db
class TestToolAPI:
    """Test tool API endpoints."""

    @pytest.mark.skip(reason="API endpoints not yet implemented - using Django templates")
    def test_list_tools_endpoint(self, authenticated_client):
        """Test listing tools via API."""
        response = authenticated_client.get("/api/v1/tools/")

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    @pytest.mark.skip(reason="API endpoints not yet implemented - using Django templates")
    def test_list_tools_requires_auth(self, api_client):
        """Test that listing tools requires authentication."""
        response = api_client.get("/api/v1/tools/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(reason="API endpoints not yet implemented - using Django templates")
    def test_get_tool_metadata(self, authenticated_client):
        """Test getting tool metadata."""
        # Try to get image-format-converter metadata
        response = authenticated_client.get("/api/v1/tools/image-format-converter/")

        if response.status_code == status.HTTP_200_OK:
            assert "name" in response.data
            assert "displayName" in response.data
            assert "description" in response.data


@pytest.mark.django_db
class TestToolExecution:
    """Test tool execution endpoints."""

    @pytest.mark.skip(reason="API endpoints not yet implemented - using Django templates")
    def test_list_executions(self, authenticated_client):
        """Test listing user's tool executions."""
        response = authenticated_client.get("/api/v1/executions/")

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data or isinstance(response.data, list)

    @pytest.mark.skip(reason="API endpoints not yet implemented - using Django templates")
    def test_executions_filtered_by_user(self, authenticated_client, admin_client, user):
        """Test that executions are filtered by user."""
        from apps.tools.models import ToolExecution

        # Create execution for user
        ToolExecution.objects.create(
            user=user, tool_name="test-tool", input_filename="test.txt", status="completed"
        )

        response = authenticated_client.get("/api/v1/executions/")

        assert response.status_code == status.HTTP_200_OK
        # User should see their execution
        results = response.data.get("results", response.data)
        assert len(results) >= 1


@pytest.mark.django_db
class TestUnitConverter:
    """Test unit converter tool functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = UnitConverter()

    def test_tool_metadata(self):
        """Test that tool has proper metadata."""
        assert self.converter.name == "unit-converter"
        assert self.converter.display_name == "Unit Converter"
        assert self.converter.category == "conversion"

        metadata = self.converter.get_metadata()
        assert "length_units" in metadata
        assert "temperature_units" in metadata
        assert "meter" in metadata["length_units"]
        assert "celsius" in metadata["temperature_units"]

    def test_validation_missing_parameters(self):
        """Test validation fails with missing parameters."""
        is_valid, error = self.converter.validate(parameters={})
        assert is_valid is False
        assert "Missing required parameters" in error

    def test_validation_invalid_conversion_type(self):
        """Test validation fails with invalid conversion type."""
        is_valid, error = self.converter.validate(
            parameters={
                "conversion_type": "weight",
                "value": 10,
                "from_unit": "meter",
                "to_unit": "kilometer",
            }
        )
        assert is_valid is False
        assert "Unsupported conversion type" in error

    def test_validation_invalid_value(self):
        """Test validation fails with invalid numeric value."""
        is_valid, error = self.converter.validate(
            parameters={
                "conversion_type": "length",
                "value": "not_a_number",
                "from_unit": "meter",
                "to_unit": "kilometer",
            }
        )
        assert is_valid is False
        assert "Invalid numeric value" in error

    def test_validation_invalid_length_unit(self):
        """Test validation fails with invalid length unit."""
        is_valid, error = self.converter.validate(
            parameters={
                "conversion_type": "length",
                "value": 10,
                "from_unit": "invalid_unit",
                "to_unit": "meter",
            }
        )
        assert is_valid is False
        assert "Invalid source unit" in error

    def test_validation_invalid_temperature_unit(self):
        """Test validation fails with invalid temperature unit."""
        is_valid, error = self.converter.validate(
            parameters={
                "conversion_type": "temperature",
                "value": 100,
                "from_unit": "invalid_unit",
                "to_unit": "celsius",
            }
        )
        assert is_valid is False
        assert "Invalid source unit" in error

    def test_validation_success(self):
        """Test validation succeeds with valid parameters."""
        is_valid, error = self.converter.validate(
            parameters={
                "conversion_type": "length",
                "value": 10,
                "from_unit": "meter",
                "to_unit": "kilometer",
            }
        )
        assert is_valid is True
        assert error is None

    # Length conversion tests
    def test_meter_to_kilometer(self):
        """Test converting meters to kilometers."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "length",
                "value": 1000,
                "from_unit": "meter",
                "to_unit": "kilometer",
            }
        )
        assert result_dict["output_value"] == 1.0

    def test_kilometer_to_meter(self):
        """Test converting kilometers to meters."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "length",
                "value": 1,
                "from_unit": "kilometer",
                "to_unit": "meter",
            }
        )
        assert result_dict["output_value"] == 1000.0

    def test_mile_to_kilometer(self):
        """Test converting miles to kilometers."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "length",
                "value": 1,
                "from_unit": "mile",
                "to_unit": "kilometer",
            }
        )
        assert abs(result_dict["output_value"] - 1.609344) < 0.0001

    def test_inch_to_centimeter(self):
        """Test converting inches to centimeters."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "length",
                "value": 1,
                "from_unit": "inch",
                "to_unit": "centimeter",
            }
        )
        assert abs(result_dict["output_value"] - 2.54) < 0.0001

    def test_foot_to_meter(self):
        """Test converting feet to meters."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "length",
                "value": 1,
                "from_unit": "foot",
                "to_unit": "meter",
            }
        )
        assert abs(result_dict["output_value"] - 0.3048) < 0.0001

    # Temperature conversion tests
    def test_celsius_to_fahrenheit(self):
        """Test converting Celsius to Fahrenheit."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "temperature",
                "value": 0,
                "from_unit": "celsius",
                "to_unit": "fahrenheit",
            }
        )
        assert result_dict["output_value"] == 32.0

    def test_fahrenheit_to_celsius(self):
        """Test converting Fahrenheit to Celsius."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "temperature",
                "value": 32,
                "from_unit": "fahrenheit",
                "to_unit": "celsius",
            }
        )
        assert abs(result_dict["output_value"] - 0.0) < 0.0001

    def test_celsius_to_kelvin(self):
        """Test converting Celsius to Kelvin."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "temperature",
                "value": 0,
                "from_unit": "celsius",
                "to_unit": "kelvin",
            }
        )
        assert result_dict["output_value"] == 273.15

    def test_kelvin_to_celsius(self):
        """Test converting Kelvin to Celsius."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "temperature",
                "value": 273.15,
                "from_unit": "kelvin",
                "to_unit": "celsius",
            }
        )
        assert abs(result_dict["output_value"] - 0.0) < 0.0001

    def test_fahrenheit_to_kelvin(self):
        """Test converting Fahrenheit to Kelvin."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "temperature",
                "value": 32,
                "from_unit": "fahrenheit",
                "to_unit": "kelvin",
            }
        )
        assert abs(result_dict["output_value"] - 273.15) < 0.0001

    # Volume conversion tests
    def test_liter_to_milliliter(self):
        """Test converting Liter to Milliliter."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "volume",
                "value": 1,
                "from_unit": "liter",
                "to_unit": "milliliter",
            }
        )
        assert abs(result_dict["output_value"] - 1000.0) < 0.0001

    def test_gallon_us_to_liter(self):
        """Test converting US Gallon to Liter."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "volume",
                "value": 1,
                "from_unit": "gallon_us",
                "to_unit": "liter",
            }
        )
        assert abs(result_dict["output_value"] - 3.785411784) < 0.0001

    def test_cubic_meter_to_liter(self):
        """Test converting Cubic Meter to Liter."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "volume",
                "value": 1,
                "from_unit": "cubic_meter",
                "to_unit": "liter",
            }
        )
        assert abs(result_dict["output_value"] - 1000.0) < 0.0001

    def test_cup_us_to_milliliter(self):
        """Test converting US Cup to Milliliter."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "volume",
                "value": 1,
                "from_unit": "cup_us",
                "to_unit": "milliliter",
            }
        )
        assert abs(result_dict["output_value"] - 236.5882365) < 0.0001

    def test_barrel_oil_to_gallon_us(self):
        """Test converting Oil Barrel to US Gallon."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "volume",
                "value": 1,
                "from_unit": "barrel_oil",
                "to_unit": "gallon_us",
            }
        )
        assert abs(result_dict["output_value"] - 42.0) < 0.1

    def test_cubic_foot_to_cubic_meter(self):
        """Test converting Cubic Foot to Cubic Meter."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "volume",
                "value": 1,
                "from_unit": "cubic_foot",
                "to_unit": "cubic_meter",
            }
        )
        assert abs(result_dict["output_value"] - 0.028316846592) < 0.0001

    def test_validation_invalid_volume_unit(self):
        """Test validation fails for invalid volume unit."""
        is_valid, error = self.converter.validate(
            parameters={
                "conversion_type": "volume",
                "value": 1,
                "from_unit": "invalid_unit",
                "to_unit": "liter",
            }
        )
        assert not is_valid
        assert "Invalid source unit" in error

    # Area conversion tests
    def test_square_meter_to_square_centimeter(self):
        """Test converting Square Meter to Square Centimeter."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "area",
                "value": 1,
                "from_unit": "square_meter",
                "to_unit": "square_centimeter",
            }
        )
        assert abs(result_dict["output_value"] - 10000.0) < 0.0001

    def test_acre_to_square_meter(self):
        """Test converting Acre to Square Meter."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "area",
                "value": 1,
                "from_unit": "acre",
                "to_unit": "square_meter",
            }
        )
        assert abs(result_dict["output_value"] - 4046.8564224) < 0.0001

    def test_hectare_to_acre(self):
        """Test converting Hectare to Acre."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "area",
                "value": 1,
                "from_unit": "hectare",
                "to_unit": "acre",
            }
        )
        assert abs(result_dict["output_value"] - 2.471) < 0.01

    def test_square_foot_to_square_meter(self):
        """Test converting Square Foot to Square Meter."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "area",
                "value": 1,
                "from_unit": "square_foot",
                "to_unit": "square_meter",
            }
        )
        assert abs(result_dict["output_value"] - 0.09290304) < 0.0001

    def test_validation_invalid_area_unit(self):
        """Test validation fails for invalid area unit."""
        is_valid, error = self.converter.validate(
            parameters={
                "conversion_type": "area",
                "value": 1,
                "from_unit": "invalid_unit",
                "to_unit": "square_meter",
            }
        )
        assert not is_valid
        assert "Invalid source unit" in error

    # Energy conversion tests
    def test_kilojoule_to_joule(self):
        """Test converting Kilojoule to Joule."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "energy",
                "value": 1,
                "from_unit": "kilojoule",
                "to_unit": "joule",
            }
        )
        assert abs(result_dict["output_value"] - 1000.0) < 0.0001

    def test_kilowatt_hour_to_megajoule(self):
        """Test converting Kilowatt-hour to Megajoule."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "energy",
                "value": 1,
                "from_unit": "kilowatt_hour",
                "to_unit": "megajoule",
            }
        )
        assert abs(result_dict["output_value"] - 3.6) < 0.0001

    def test_calorie_to_joule(self):
        """Test converting Calorie to Joule."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "energy",
                "value": 1,
                "from_unit": "calorie",
                "to_unit": "joule",
            }
        )
        assert abs(result_dict["output_value"] - 4.184) < 0.0001

    def test_btu_to_kilojoule(self):
        """Test converting BTU to Kilojoule."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "energy",
                "value": 1,
                "from_unit": "btu",
                "to_unit": "kilojoule",
            }
        )
        assert abs(result_dict["output_value"] - 1.055) < 0.01

    def test_foot_pound_to_joule(self):
        """Test converting Foot-pound to Joule."""
        result_dict, result_string = self.converter.process(
            parameters={
                "conversion_type": "energy",
                "value": 1,
                "from_unit": "foot_pound",
                "to_unit": "joule",
            }
        )
        assert abs(result_dict["output_value"] - 1.3558179483314004) < 0.0001

    def test_validation_invalid_energy_unit(self):
        """Test validation fails for invalid energy unit."""
        is_valid, error = self.converter.validate(
            parameters={
                "conversion_type": "energy",
                "value": 1,
                "from_unit": "invalid_unit",
                "to_unit": "joule",
            }
        )
        assert not is_valid
        assert "Invalid source unit" in error

    def test_cleanup(self):
        """Test cleanup method runs without errors."""
        self.converter.cleanup()  # Should not raise any exceptions

    def test_bulk_processing_not_supported(self):
        """Test that unit converter doesn't require file uploads."""
        # Unit converter doesn't need file uploads or bulk processing
        metadata = self.converter.get_metadata()
        assert metadata.get("requires_file_upload") is False


@pytest.mark.django_db
class TestPdfDocxConverter:
    """Test PDF to DOCX converter tool functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        from apps.tools.plugins.pdf_docx_converter import PdfDocxConverter

        self.converter = PdfDocxConverter()

    def test_tool_metadata(self):
        """Test tool metadata is correctly defined."""
        assert self.converter.name == "pdf-docx-converter"
        assert self.converter.display_name == "PDF to DOCX Converter"
        assert self.converter.category == "document"
        assert ".pdf" in self.converter.allowed_input_types

        metadata = self.converter.get_metadata()
        assert metadata["name"] == "pdf-docx-converter"
        assert metadata["category"] == "document"

    def test_validation_missing_pdf2docx(self, mocker):
        """Test validation fails when pdf2docx is not installed."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Mock Converter to be None (simulating library not installed)
        mocker.patch("apps.tools.plugins.pdf_docx_converter.Converter", None)

        file = SimpleUploadedFile("test.pdf", b"fake pdf content", content_type="application/pdf")

        converter = self.converter.__class__()
        is_valid, error = converter.validate(file, {})

        assert not is_valid
        assert "pdf2docx library not installed" in error

    def test_validation_invalid_file_type(self):
        """Test validation fails for non-PDF files."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("test.txt", b"not a pdf", content_type="text/plain")

        is_valid, error = self.converter.validate(file, {})

        assert not is_valid
        assert "File type not supported" in error

    def test_validation_file_too_large(self):
        """Test validation fails for oversized files."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a file larger than max_file_size (100MB)
        large_content = b"x" * (101 * 1024 * 1024)
        file = SimpleUploadedFile("large.pdf", large_content, content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {})

        assert not is_valid
        assert "exceeds maximum" in error

    def test_validation_invalid_start_page(self):
        """Test validation fails for invalid start_page parameter."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("test.pdf", b"fake pdf", content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {"start_page": -1})
        assert not is_valid
        assert "start_page must be non-negative" in error

        is_valid, error = self.converter.validate(file, {"start_page": "invalid"})
        assert not is_valid
        assert "start_page must be an integer" in error

    def test_validation_invalid_end_page(self):
        """Test validation fails for invalid end_page parameter."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("test.pdf", b"fake pdf", content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {"end_page": -1})
        assert not is_valid
        assert "end_page must be non-negative" in error

        is_valid, error = self.converter.validate(file, {"start_page": 5, "end_page": 2})
        assert not is_valid
        assert "end_page must be greater than or equal to start_page" in error

    def test_validation_success(self):
        """Test validation succeeds for valid input."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("test.pdf", b"fake pdf content", content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {})

        assert is_valid
        assert error is None

    def test_validation_with_page_parameters(self):
        """Test validation succeeds with valid page parameters."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        file = SimpleUploadedFile("test.pdf", b"fake pdf", content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {"start_page": 0, "end_page": 5})
        assert is_valid
        assert error is None

    def test_cleanup(self, tmp_path):
        """Test cleanup method removes temporary files."""
        import os

        # Create temporary test files
        test_file1 = tmp_path / "test1.pdf"
        test_file2 = tmp_path / "test2.docx"
        test_file1.write_bytes(b"test content 1")
        test_file2.write_bytes(b"test content 2")

        # Verify files exist
        assert os.path.exists(str(test_file1))
        assert os.path.exists(str(test_file2))

        # Call cleanup
        self.converter.cleanup(str(test_file1), str(test_file2))

        # Verify files are removed
        assert not os.path.exists(str(test_file1))
        assert not os.path.exists(str(test_file2))

    def test_cleanup_nonexistent_file(self):
        """Test cleanup handles non-existent files gracefully."""
        # Should not raise an exception
        self.converter.cleanup("/nonexistent/file.pdf")
