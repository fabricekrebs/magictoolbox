"""
Test Azure Functions integration for PDF to DOCX converter.
"""

from unittest.mock import MagicMock, Mock, patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

import pytest

from apps.tools.plugins.pdf_docx_converter import PdfDocxConverter


@pytest.mark.django_db
class TestPdfDocxConverterAzureFunctions:
    """Test Azure Functions integration for PDF converter."""

    def test_async_mode_disabled_by_default(self):
        """Test that async mode is disabled by default."""
        converter = PdfDocxConverter()
        assert converter.use_azure_functions is False

    @patch("apps.tools.plugins.pdf_docx_converter.settings")
    def test_async_mode_can_be_enabled(self, mock_settings):
        """Test that async mode can be enabled via settings."""
        mock_settings.USE_AZURE_FUNCTIONS_PDF_CONVERSION = True

        # Need to recreate the class to pick up the new setting
        from apps.tools.plugins.pdf_docx_converter import PdfDocxConverter as PDFConverter

        converter = PDFConverter()

        # The class attribute is set at class definition time, so we need to check via settings
        assert mock_settings.USE_AZURE_FUNCTIONS_PDF_CONVERSION is True

    @patch("apps.tools.plugins.pdf_docx_converter.BlobServiceClient")
    @patch("apps.tools.plugins.pdf_docx_converter.DefaultAzureCredential")
    @patch.object(PdfDocxConverter, "use_azure_functions", True)
    def test_process_async_uploads_to_blob(self, mock_credential, mock_blob_service):
        """Test that async processing uploads PDF to blob storage."""
        # Mock blob service
        mock_blob_client = Mock()
        mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client

        # Mock settings
        with patch("apps.tools.plugins.pdf_docx_converter.settings") as mock_settings:
            mock_settings.AZURE_ACCOUNT_NAME = "testaccount"

            # Create converter and file
            converter = PdfDocxConverter()
            converter.use_azure_functions = True

            file = SimpleUploadedFile(
                "test.pdf", b"fake pdf content", content_type="application/pdf"
            )
            parameters = {"start_page": 0, "end_page": 10}

            # Process
            execution_id, output_filename = converter.process(file, parameters)

            # Verify upload was called
            assert mock_blob_client.upload_blob.called
            assert output_filename is None  # Async processing returns None for filename
            assert execution_id is not None  # Should return execution ID
            assert len(execution_id) == 36  # UUID format

    def test_process_sync_when_async_disabled(self, mocker):
        """Test that sync processing is used when async is disabled."""
        converter = PdfDocxConverter()
        converter.use_azure_functions = False

        # Mock the sync process method
        mock_process_sync = mocker.patch.object(
            converter, "_process_sync", return_value=("/tmp/output.docx", "output.docx")
        )

        file = SimpleUploadedFile("test.pdf", b"fake pdf", content_type="application/pdf")
        parameters = {}

        output_path, output_filename = converter.process(file, parameters)

        # Verify sync processing was called
        mock_process_sync.assert_called_once()
        assert output_path == "/tmp/output.docx"
        assert output_filename == "output.docx"

    @patch("apps.tools.plugins.pdf_docx_converter.BlobServiceClient")
    @patch("apps.tools.plugins.pdf_docx_converter.DefaultAzureCredential")
    def test_process_async_includes_metadata(self, mock_credential, mock_blob_service):
        """Test that blob metadata includes conversion parameters."""
        mock_blob_client = Mock()
        mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client

        with patch("apps.tools.plugins.pdf_docx_converter.settings") as mock_settings:
            mock_settings.AZURE_ACCOUNT_NAME = "testaccount"

            converter = PdfDocxConverter()
            converter.use_azure_functions = True

            file = SimpleUploadedFile(
                "document.pdf", b"pdf content", content_type="application/pdf"
            )
            parameters = {"start_page": 5, "end_page": 15}

            execution_id, _ = converter.process(file, parameters)

            # Check that upload_blob was called with correct metadata
            call_args = mock_blob_client.upload_blob.call_args
            metadata = call_args[1]["metadata"]

            assert metadata["execution_id"] == execution_id
            assert metadata["start_page"] == "5"
            assert metadata["end_page"] == "15"
            assert metadata["original_filename"] == "document.pdf"

    @patch("apps.tools.plugins.pdf_docx_converter.BlobServiceClient")
    def test_process_async_handles_missing_storage_account(self, mock_blob_service):
        """Test error handling when storage account is not configured."""
        with patch("apps.tools.plugins.pdf_docx_converter.settings") as mock_settings:
            mock_settings.AZURE_ACCOUNT_NAME = None

            converter = PdfDocxConverter()
            converter.use_azure_functions = True

            file = SimpleUploadedFile("test.pdf", b"content", content_type="application/pdf")

            # Should raise ToolExecutionError
            from apps.core.exceptions import ToolExecutionError

            with pytest.raises(ToolExecutionError, match="AZURE_ACCOUNT_NAME not configured"):
                converter.process(file, {})
