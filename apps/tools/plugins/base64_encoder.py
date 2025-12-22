"""
Base64 Encoder/Decoder Tool

Supports bidirectional encoding and decoding of text content.
Can process direct text input or uploaded text files.
"""

import base64
from typing import Any, Dict, Optional, Tuple

from django.core.files.uploadedfile import UploadedFile

from apps.tools.base import BaseTool


class Base64Encoder(BaseTool):
    """Tool for encoding and decoding Base64 text."""

    name = "base64-encoder"
    display_name = "Base64 Encoder/Decoder"
    description = "Encode text to Base64 or decode Base64 back to text. Supports direct text input or file upload (max 10MB)."
    category = "conversion"
    version = "1.0.0"
    icon = "file-binary"

    allowed_input_types = [".txt", ".text"]
    max_file_size = 10 * 1024 * 1024  # 10MB
    requires_file_upload = False

    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata."""
        base_metadata = super().get_metadata()
        base_metadata.update(
            {
                "modes": ["encode", "decode"],
                "max_text_size": self.max_file_size,
                "requires_file_upload": False,
                "supports_text_input": True,
            }
        )
        return base_metadata

    def validate(
        self,
        input_file: Optional[UploadedFile] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input text or file and parameters.

        Args:
            input_file: Optional uploaded text file
            parameters: Must contain 'mode' (encode/decode) and optionally 'text'

        Returns:
            Tuple of (is_valid, error_message)
        """
        if parameters is None:
            parameters = {}

        mode = parameters.get("mode", "").lower()
        text_input = parameters.get("text", "")

        # Validate mode
        if mode not in ["encode", "decode"]:
            return False, "Invalid mode. Must be 'encode' or 'decode'."

        # Check if we have either text input or file upload
        if not text_input and not input_file:
            return False, "No text input or file provided."

        # Validate file if provided
        if input_file:
            # Check file size
            if input_file.size > self.max_file_size:
                max_mb = self.max_file_size / (1024 * 1024)
                return False, f"File size exceeds maximum limit of {max_mb}MB."

            # Check file type (optional - be lenient)
            file_ext = f".{input_file.name.split('.')[-1].lower()}"
            if file_ext not in self.allowed_input_types and file_ext != ".":
                self.logger.warning(
                    f"File type {file_ext} not in allowed types, but processing anyway"
                )

        # Validate text input size
        if text_input:
            text_size = len(text_input.encode("utf-8"))
            if text_size > self.max_file_size:
                max_mb = self.max_file_size / (1024 * 1024)
                return False, f"Text input exceeds maximum limit of {max_mb}MB."

        # For decode mode, validate base64 format
        if mode == "decode":
            test_text = text_input
            if input_file and not test_text:
                # Read a sample from file to validate
                try:
                    input_file.seek(0)
                    test_text = input_file.read(1000).decode("utf-8")
                    input_file.seek(0)  # Reset for later processing
                except Exception as e:
                    return False, f"Cannot read file for validation: {str(e)}"

            if test_text:
                # Basic base64 validation (check if it looks like base64)
                import re

                if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", test_text.strip()):
                    return False, "Invalid Base64 format. Text contains invalid characters."

        return True, None

    def process(
        self,
        input_file: Optional[UploadedFile] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], None]:
        """
        Execute Base64 encoding or decoding.

        Args:
            input_file: Optional uploaded text file
            parameters: Must contain 'mode' and optionally 'text'

        Returns:
            Tuple of (result_dict, None) - None signals synchronous processing

        Raises:
            Exception: If encoding/decoding fails
        """
        if parameters is None:
            parameters = {}

        mode = parameters.get("mode", "").lower()
        text_input = parameters.get("text", "")

        try:
            # Get text content from input or file
            if input_file:
                self.logger.info(f"📄 Processing file: {input_file.name}")
                input_file.seek(0)
                content = input_file.read().decode("utf-8")
            else:
                self.logger.info("📝 Processing direct text input")
                content = text_input

            # Perform operation
            if mode == "encode":
                self.logger.info("🔒 Encoding to Base64")
                encoded_bytes = base64.b64encode(content.encode("utf-8"))
                result = encoded_bytes.decode("ascii")
                operation = "encoded"
            else:  # decode
                self.logger.info("🔓 Decoding from Base64")
                # Remove whitespace/newlines that might have been added for readability
                clean_content = content.replace("\n", "").replace("\r", "").replace(" ", "")
                decoded_bytes = base64.b64decode(clean_content)
                result = decoded_bytes.decode("utf-8")
                operation = "decoded"

            self.logger.info(f"✅ Successfully {operation} {len(content)} characters")

            # Return result as JSON (save to temp file for API return)
            result_data = {
                "result": result,
                "mode": mode,
                "operation": operation,
                "input_length": len(content),
                "output_length": len(result),
            }

            import json
            import os
            import tempfile

            temp_fd, temp_path = tempfile.mkstemp(suffix=".json", prefix="base64_")
            os.close(temp_fd)

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(result_data, f, indent=2, ensure_ascii=False)

            # Return path to JSON file and filename
            return temp_path, "base64_result.json"

        except base64.binascii.Error as e:
            self.logger.error(f"❌ Base64 error: {str(e)}")
            raise Exception(f"Invalid Base64 input: {str(e)}")
        except UnicodeDecodeError as e:
            self.logger.error(f"❌ Unicode error: {str(e)}")
            raise Exception(f"Cannot decode result as UTF-8 text: {str(e)}")
        except Exception as e:
            self.logger.error(f"❌ Processing failed: {str(e)}")
            raise Exception(f"Processing failed: {str(e)}")

    def cleanup(self, *file_paths: str) -> None:
        """
        Clean up temporary files (not needed for this tool).

        Args:
            *file_paths: Paths to temporary files
        """
        # No file cleanup needed for synchronous text processing
        pass
