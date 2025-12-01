"""
Tests specifically for PDF to DOCX converter.
"""

import os

from django.core.files.uploadedfile import SimpleUploadedFile

import pytest

from apps.tools.plugins.pdf_docx_converter import PdfDocxConverter


@pytest.mark.django_db
class TestPdfDocxConverter:
    """Test PDF to DOCX converter tool functionality."""

    def setup_method(self):
        """Set up test fixtures."""
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
        # Mock Converter to be None (simulating library not installed)
        mocker.patch("apps.tools.plugins.pdf_docx_converter.Converter", None)

        file = SimpleUploadedFile("test.pdf", b"fake pdf content", content_type="application/pdf")

        converter = self.converter.__class__()
        is_valid, error = converter.validate(file, {})

        assert not is_valid
        assert "pdf2docx library not installed" in error

    def test_validation_invalid_file_type(self):
        """Test validation fails for non-PDF files."""
        file = SimpleUploadedFile("test.txt", b"not a pdf", content_type="text/plain")

        is_valid, error = self.converter.validate(file, {})

        assert not is_valid
        assert "File type not supported" in error

    def test_validation_file_too_large(self):
        """Test validation fails for oversized files."""
        # Create a file larger than max_file_size (100MB)
        large_content = b"x" * (101 * 1024 * 1024)
        file = SimpleUploadedFile("large.pdf", large_content, content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {})

        assert not is_valid
        assert "exceeds maximum" in error

    def test_validation_invalid_start_page(self):
        """Test validation fails for invalid start_page parameter."""
        file = SimpleUploadedFile("test.pdf", b"fake pdf", content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {"start_page": -1})
        assert not is_valid
        assert "start_page must be non-negative" in error

        is_valid, error = self.converter.validate(file, {"start_page": "invalid"})
        assert not is_valid
        assert "start_page must be an integer" in error

    def test_validation_invalid_end_page(self):
        """Test validation fails for invalid end_page parameter."""
        file = SimpleUploadedFile("test.pdf", b"fake pdf", content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {"end_page": -1})
        assert not is_valid
        assert "end_page must be non-negative" in error

        is_valid, error = self.converter.validate(file, {"start_page": 5, "end_page": 2})
        assert not is_valid
        assert "end_page must be greater than or equal to start_page" in error

    def test_validation_success(self):
        """Test validation succeeds for valid input."""
        file = SimpleUploadedFile("test.pdf", b"fake pdf content", content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {})

        assert is_valid
        assert error is None

    def test_validation_with_page_parameters(self):
        """Test validation succeeds with valid page parameters."""
        file = SimpleUploadedFile("test.pdf", b"fake pdf", content_type="application/pdf")

        is_valid, error = self.converter.validate(file, {"start_page": 0, "end_page": 5})
        assert is_valid
        assert error is None

    def test_cleanup(self, tmp_path):
        """Test cleanup method removes temporary files."""
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
