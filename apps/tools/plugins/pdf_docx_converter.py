"""
PDF to DOCX converter tool.

Converts PDF documents to Microsoft Word DOCX format.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError
from apps.tools.base import BaseTool

try:
    from pdf2docx import Converter
except ImportError:
    Converter = None


class PdfDocxConverter(BaseTool):
    """
    Convert PDF documents to DOCX format.

    Preserves text, images, tables, and basic formatting.
    """

    # Tool metadata
    name = "pdf-docx-converter"
    display_name = "PDF to DOCX Converter"
    description = (
        "Convert PDF documents to Microsoft Word DOCX format. "
        "Preserves text, images, tables, and formatting where possible."
    )
    category = "document"
    version = "1.0.0"
    icon = "file-earmark-word"

    # File constraints
    allowed_input_types = [".pdf"]
    max_file_size = 100 * 1024 * 1024  # 100MB per file

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and parameters.

        Optional parameters:
        - start_page: First page to convert (default: 0)
        - end_page: Last page to convert (default: None for all pages)
        """
        # Check pdf2docx is installed
        if Converter is None:
            return False, "pdf2docx library not installed"

        # Validate file type
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"

        # Validate file size
        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"

        # Validate start_page parameter (if provided)
        start_page = parameters.get("start_page")
        if start_page is not None:
            try:
                start_page = int(start_page)
                if start_page < 0:
                    return False, "start_page must be non-negative"
            except (ValueError, TypeError):
                return False, "start_page must be an integer"

        # Validate end_page parameter (if provided)
        end_page = parameters.get("end_page")
        if end_page is not None:
            try:
                end_page = int(end_page)
                if end_page < 0:
                    return False, "end_page must be non-negative"
                if start_page is not None and end_page < start_page:
                    return False, "end_page must be greater than or equal to start_page"
            except (ValueError, TypeError):
                return False, "end_page must be an integer"

        return True, None

    def process(self, input_file: UploadedFile, parameters: Dict[str, Any]) -> Tuple[str, str]:
        """
        Convert PDF to DOCX format.

        Returns:
            Tuple of (output_file_path, output_filename)
        """
        start_page = parameters.get("start_page", 0)
        end_page = parameters.get("end_page")

        # Convert to int if provided
        if start_page is not None:
            start_page = int(start_page)
        if end_page is not None:
            end_page = int(end_page)

        temp_input = None
        temp_output = None

        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_in:
                for chunk in input_file.chunks():
                    tmp_in.write(chunk)
                temp_input = tmp_in.name

            # Create output file path
            output_filename = f"{Path(input_file.name).stem}.docx"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_out:
                temp_output = tmp_out.name

            # Convert PDF to DOCX
            self.logger.info(
                f"Converting PDF to DOCX: {input_file.name} "
                f"(pages: {start_page}-{end_page if end_page else 'end'})"
            )

            cv = Converter(temp_input)
            cv.convert(temp_output, start=start_page, end=end_page)
            cv.close()

            output_size = os.path.getsize(temp_output)
            self.logger.info(
                f"Successfully converted {input_file.name} to DOCX ({output_size / 1024:.1f} KB)"
            )

            # Cleanup input temp file
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)

            return temp_output, output_filename

        except Exception as e:
            self.logger.error(f"PDF to DOCX conversion failed: {e}", exc_info=True)

            # Cleanup on error
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            if temp_output and os.path.exists(temp_output):
                os.unlink(temp_output)

            raise ToolExecutionError(f"PDF to DOCX conversion failed: {str(e)}")

    def cleanup(self, *file_paths: str) -> None:
        """Remove temporary files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
