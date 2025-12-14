"""
OCR Text Extraction Tool

Extracts text from images using Tesseract OCR with multiple language support.
Supports image preprocessing for improved accuracy.
"""

import os
import uuid
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from apps.core.exceptions import ToolExecutionError
from apps.tools.base import BaseTool

try:
    from azure.identity import AzureCliCredential, DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    AzureCliCredential = None
    DefaultAzureCredential = None
    BlobServiceClient = None


class OCRTool(BaseTool):
    """
    Extract text from images using OCR (Optical Character Recognition).

    Supports multiple languages and image preprocessing for better accuracy.
    """

    # Tool metadata
    name = "ocr-tool"
    display_name = "OCR Text Extractor"
    description = (
        "Extract text from images using OCR (Optical Character Recognition). "
        "Supports multiple languages and image preprocessing for improved accuracy."
    )
    category = "image"
    version = "1.0.0"
    icon = "file-text"

    # File constraints
    allowed_input_types = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"]
    max_file_size = 50 * 1024 * 1024  # 50MB

    # Supported languages
    SUPPORTED_LANGUAGES = {
        "eng": "English",
        "fra": "French",
        "deu": "German",
        "spa": "Spanish",
        "ita": "Italian",
        "por": "Portuguese",
        "nld": "Dutch",
        "rus": "Russian",
        "jpn": "Japanese",
        "chi_sim": "Chinese (Simplified)",
        "chi_tra": "Chinese (Traditional)",
        "kor": "Korean",
        "ara": "Arabic",
        "hin": "Hindi",
    }

    # OCR page segmentation modes
    OCR_MODES = {
        "0": "Orientation and script detection only",
        "1": "Automatic page segmentation with OSD",
        "3": "Fully automatic page segmentation (default)",
        "4": "Single column of text (variable sizes)",
        "6": "Single uniform block of text",
        "11": "Sparse text - find as much text as possible",
        "12": "Sparse text with OSD",
    }

    def get_metadata(self) -> Dict[str, Any]:
        """Return tool metadata including supported languages."""
        base_metadata = super().get_metadata()
        base_metadata.update({
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "ocr_modes": self.OCR_MODES,
            "default_language": "eng",
            "default_ocr_mode": "3",
            "supports_preprocessing": True,
            "max_file_size_mb": self.max_file_size / (1024 * 1024),
        })
        return base_metadata

    def validate(
        self, input_file: UploadedFile, parameters: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate input file and parameters.

        Optional parameters:
        - language: Language code (default: 'eng')
        - ocr_mode: Page segmentation mode 0-12 (default: '3')
        - preprocess: Enable image preprocessing (default: True)
        """
        # Validate file type
        if not self.validate_file_type(input_file.name):
            return False, f"File type not supported. Allowed: {', '.join(self.allowed_input_types)}"

        # Validate file size
        if not self.validate_file_size(input_file):
            return False, f"File size exceeds maximum of {self.max_file_size / (1024*1024):.1f}MB"

        # Validate language parameter
        language = parameters.get("language", "eng")
        if language not in self.SUPPORTED_LANGUAGES:
            return False, f"Unsupported language '{language}'. Supported: {', '.join(self.SUPPORTED_LANGUAGES.keys())}"

        # Validate OCR mode parameter
        ocr_mode = str(parameters.get("ocr_mode", "3"))
        if ocr_mode not in self.OCR_MODES:
            return False, f"Invalid OCR mode '{ocr_mode}'. Supported: {', '.join(self.OCR_MODES.keys())}"

        # Validate preprocess parameter
        preprocess = parameters.get("preprocess", True)
        if not isinstance(preprocess, bool):
            # Try to convert string to bool
            if isinstance(preprocess, str):
                preprocess_lower = preprocess.lower()
                if preprocess_lower not in ["true", "false", "1", "0", "yes", "no"]:
                    return False, "Invalid preprocess value. Must be true or false."
            else:
                return False, "Invalid preprocess value. Must be boolean."

        return True, None

    def process(
        self, input_file: UploadedFile, parameters: Dict[str, Any], execution_id: str = None
    ) -> Tuple[str, None]:
        """
        Upload image to blob storage for async OCR processing by Azure Function.

        Args:
            input_file: The image file to process
            parameters: OCR parameters (language, ocr_mode, preprocess)
            execution_id: Optional pre-generated execution ID

        Returns:
            Tuple of (execution_id, None) to signal async processing
        """
        try:
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ToolExecutionError(
                "Azure SDK not installed. Install azure-storage-blob and azure-identity."
            )

        # Use provided execution ID or generate new one
        if execution_id is None:
            execution_id = str(uuid.uuid4())

        # Get file extension
        file_ext = f".{input_file.name.split('.')[-1].lower()}"
        blob_name = f"image/{execution_id}{file_ext}"

        self.logger.info("=" * 80)
        self.logger.info("📤 STARTING IMAGE UPLOAD FOR ASYNC OCR PROCESSING")
        self.logger.info(f"   Execution ID: {execution_id}")
        self.logger.info(f"   Original filename: {input_file.name}")
        self.logger.info(f"   File size: {input_file.size:,} bytes")
        self.logger.info(f"   Target blob: {blob_name}")
        self.logger.info(f"   Parameters: {parameters}")
        self.logger.info("=" * 80)

        try:
            # Detect environment and get appropriate blob service client
            connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

            if connection_string and "127.0.0.1" in connection_string:
                # Local development with Azurite
                self.logger.info("🔧 Using local Azurite for blob storage")
                self.logger.info(f"   Connection string: {connection_string[:50]}...")
                blob_service = BlobServiceClient.from_connection_string(connection_string)
                self.logger.info("✅ BlobServiceClient created successfully (Azurite)")
            else:
                # Production with Azure Managed Identity
                storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None) or getattr(settings, "AZURE_ACCOUNT_NAME", None)
                if not storage_account_name:
                    self.logger.error("❌ Storage account name not configured")
                    raise ToolExecutionError(
                        "AZURE_STORAGE_ACCOUNT_NAME or AZURE_ACCOUNT_NAME not configured for production environment"
                    )

                account_url = f"https://{storage_account_name}.blob.core.windows.net"
                self.logger.info(f"   Storage URL: {account_url}")

                # Use AzureCliCredential for local/testing, DefaultAzureCredential for production
                use_cli_auth = os.getenv("USE_AZURE_CLI_AUTH", "false").lower() == "true" or settings.DEBUG

                if use_cli_auth:
                    self.logger.info(
                        f"🔐 Using Azure CLI credential for storage account: {storage_account_name}"
                    )
                    credential = AzureCliCredential()
                else:
                    self.logger.info(
                        f"🔐 Using Azure Managed Identity for storage account: {storage_account_name}"
                    )
                    credential = DefaultAzureCredential()

                blob_service = BlobServiceClient(account_url=account_url, credential=credential)
                self.logger.info("✅ BlobServiceClient created successfully")

            # Get blob client
            self.logger.info(f"📦 Getting blob client for container: uploads, blob: {blob_name}")
            blob_client = blob_service.get_blob_client(container="uploads", blob=blob_name)
            self.logger.info("✅ Blob client obtained")

            # Prepare metadata for Azure Function
            metadata = {
                "execution_id": execution_id,
                "language": str(parameters.get("language", "eng")),
                "ocr_mode": str(parameters.get("ocr_mode", "3")),
                "preprocess": str(parameters.get("preprocess", True)).lower(),
                "original_filename": input_file.name,
            }
            self.logger.info(f"📋 Blob metadata prepared: {metadata}")

            # Upload image to blob storage
            self.logger.info(f"⬆️  Uploading image to blob storage: {blob_name}")
            file_content = input_file.read()
            self.logger.info(f"   Read {len(file_content):,} bytes from uploaded file")

            blob_client.upload_blob(file_content, metadata=metadata, overwrite=True)

            self.logger.info("✅ Image uploaded successfully to Azure Blob Storage")
            self.logger.info(f"   Blob name: {blob_name}")
            self.logger.info(f"   Container: uploads")
            self.logger.info(f"   Size: {len(file_content):,} bytes")
            self.logger.info(f"   Execution ID: {execution_id}")

            # Trigger Azure Function via HTTP
            self.logger.info("=" * 80)
            self.logger.info("🚀 TRIGGERING AZURE FUNCTION FOR OCR PROCESSING")
            try:
                import requests
                base_url = getattr(settings, "AZURE_FUNCTION_BASE_URL", None)

                if base_url:
                    # Construct full URL by appending endpoint
                    function_url = f"{base_url}/image/ocr"
                    payload = {
                        "execution_id": execution_id,
                        "blob_name": f"uploads/{blob_name}",
                        "language": metadata["language"],
                        "ocr_mode": metadata["ocr_mode"],
                        "preprocess": metadata["preprocess"],
                    }
                    self.logger.info(f"   Function URL: {function_url}")
                    self.logger.info(f"   Payload: {payload}")
                    self.logger.info("   Sending async POST request...")

                    # Use a background thread to avoid blocking the upload response
                    import threading

                    def trigger_function_async():
                        """Background thread to trigger Azure Function."""
                        try:
                            response = requests.post(function_url, json=payload, timeout=300)

                            self.logger.info(f"📨 Response received from Azure Function")
                            self.logger.info(f"   Status code: {response.status_code}")

                            if response.status_code == 200:
                                self.logger.info("✅ Azure Function triggered successfully")
                                try:
                                    response_json = response.json()
                                    self.logger.info(f"   Response JSON: {response_json}")

                                    # Update the database if Azure Function succeeded
                                    if response_json.get('status') == 'success':
                                        self.logger.info("=" * 80)
                                        self.logger.info("📝 UPDATING DATABASE FROM AZURE FUNCTION RESPONSE")
                                        from apps.tools.models import ToolExecution
                                        from django.utils import timezone

                                        try:
                                            execution = ToolExecution.objects.get(id=execution_id)

                                            # Extract output filename from blob path
                                            output_blob = response_json.get('output_blob', '')
                                            output_filename = output_blob.split('/')[-1] if output_blob else ''

                                            # Calculate duration in seconds
                                            completed_at = timezone.now()
                                            duration_seconds = None
                                            if execution.created_at:
                                                duration_seconds = (completed_at - execution.created_at).total_seconds()

                                            # Update all fields
                                            execution.status = 'completed'
                                            execution.output_blob_path = output_blob
                                            execution.output_filename = output_filename
                                            execution.output_size = response_json.get('output_size_bytes')
                                            execution.completed_at = completed_at
                                            execution.duration_seconds = duration_seconds
                                            execution.save(update_fields=[
                                                'status', 'output_blob_path', 'output_filename',
                                                'output_size', 'completed_at', 'duration_seconds', 'updated_at'
                                            ])

                                            self.logger.info(f"✅ Database updated successfully")
                                            self.logger.info(f"   Status: completed")
                                            self.logger.info(f"   Output filename: {output_filename}")
                                        except ToolExecution.DoesNotExist:
                                            self.logger.error(f"❌ ToolExecution not found: {execution_id}")
                                        except Exception as db_err:
                                            self.logger.error(f"❌ Failed to update database: {db_err}")
                                        finally:
                                            self.logger.info("=" * 80)
                                except Exception as json_err:
                                    self.logger.warning(f"⚠️  Failed to parse JSON response: {json_err}")
                            else:
                                self.logger.warning(
                                    f"⚠️  Azure Function returned non-200 status: {response.status_code}"
                                )
                        except Exception as e:
                            self.logger.error(f"❌ Azure Function call failed in background: {e}")

                    # Start background thread and return immediately
                    thread = threading.Thread(target=trigger_function_async, daemon=True)
                    thread.start()
                    self.logger.info("✅ Azure Function trigger started in background thread")
                else:
                    self.logger.warning(
                        "⚠️  AZURE_FUNCTION_BASE_URL not configured. "
                        "Relying on blob trigger (may not work with Flex Consumption)."
                    )
            except Exception as http_error:
                self.logger.error(f"❌ Failed to trigger Azure Function via HTTP: {http_error}")

            # Return execution ID to signal async processing
            self.logger.info("=" * 80)
            self.logger.info("✅ ASYNC IMAGE UPLOAD AND TRIGGER COMPLETED")
            self.logger.info(f"   Execution ID: {execution_id}")
            self.logger.info(f"   Status: Pending async OCR processing")
            self.logger.info("=" * 80)
            return execution_id, None

        except Exception as e:
            self.logger.error("=" * 80)
            self.logger.error(f"❌ FAILED TO UPLOAD IMAGE TO BLOB STORAGE")
            self.logger.error(f"   Execution ID: {execution_id}")
            self.logger.error(f"   Error type: {type(e).__name__}")
            self.logger.error(f"   Error message: {str(e)}")
            self.logger.error("=" * 80)
            self.logger.error(f"Full traceback:", exc_info=True)
            raise ToolExecutionError(f"Failed to upload image for OCR processing: {str(e)}")

    def cleanup(self, *file_paths: str) -> None:
        """Remove temporary files."""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
                    self.logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
