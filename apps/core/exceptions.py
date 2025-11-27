"""
Custom exceptions for MagicToolbox.

Provides structured error handling with consistent API responses.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class BaseAPIException(APIException):
    """Base exception class for all custom API exceptions."""

    def __init__(self, detail=None, code=None):
        if detail is not None:
            self.detail = detail
        if code is not None:
            self.code = code
        super().__init__(detail, code)


class ToolExecutionError(BaseAPIException):
    """Raised when a tool execution fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Tool execution failed"
    default_code = "tool_execution_error"


class ToolValidationError(BaseAPIException):
    """Raised when tool input validation fails."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Tool validation failed"
    default_code = "tool_validation_error"


class ToolNotFoundError(BaseAPIException):
    """Raised when requested tool is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Tool not found"
    default_code = "tool_not_found"


class FileUploadError(BaseAPIException):
    """Raised when file upload fails validation or processing."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "File upload failed"
    default_code = "file_upload_error"


class FileSizeExceededError(BaseAPIException):
    """Raised when uploaded file exceeds size limit."""

    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = "File size exceeds maximum allowed size"
    default_code = "file_size_exceeded"


class InvalidFileTypeError(BaseAPIException):
    """Raised when uploaded file type is not allowed."""

    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_detail = "File type not allowed"
    default_code = "invalid_file_type"


class RateLimitExceededError(BaseAPIException):
    """Raised when rate limit is exceeded."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Rate limit exceeded"
    default_code = "rate_limit_exceeded"


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that provides consistent error responses.

    Returns:
        Response with structure:
        {
            "error": {
                "message": "Human-readable error message",
                "code": "machine_readable_error_code",
                "details": {...}  # Optional additional details
            }
        }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # Handle Django validation errors
    if isinstance(exc, DjangoValidationError):
        response = exception_handler(APIException(exc.messages), context)

    if response is not None:
        # Get request ID if available
        request = context.get("request")
        request_id = getattr(request, "id", None)

        # Restructure error response
        error_response = {
            "error": {
                "message": str(response.data.get("detail", "An error occurred")),
                "code": getattr(exc, "default_code", "error"),
            }
        }

        # Add request ID if available
        if request_id:
            error_response["error"]["requestId"] = request_id

        # Add additional details if present
        if hasattr(exc, "get_full_details"):
            details = exc.get_full_details()
            if isinstance(details, dict) and len(details) > 1:
                error_response["error"]["details"] = details

        response.data = error_response

        # Log error
        logger.error(
            f"API Error: {error_response['error']['message']}",
            extra={
                "request_id": request_id,
                "error_code": error_response["error"]["code"],
                "status_code": response.status_code,
                "path": request.path if request else None,
            },
            exc_info=True,
        )

    return response
