"""
Azure Function task trigger for async processing.

Handles HTTP POST requests to Azure Functions with retry logic.
"""

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class AsyncTaskTrigger:
    """
    Trigger Azure Functions for asynchronous tool processing.

    Includes retry logic with exponential backoff for transient failures.
    """

    def __init__(self):
        """Initialize with base URL from settings."""
        self.base_url = getattr(settings, "AZURE_FUNCTION_BASE_URL", "")
        if not self.base_url:
            logger.warning(
                "⚠️ AZURE_FUNCTION_BASE_URL not configured - async tools will fail"
            )

    @retry(
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def trigger_function(
        self,
        category: str,
        action: str,
        payload: Dict[str, Any],
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Trigger Azure Function with retry logic.

        Args:
            category: Tool category (pdf, video, image, etc.)
            action: Action to perform (convert, rotate, resize, etc.)
            payload: Request payload with execution details
            timeout: Request timeout in seconds

        Returns:
            Response JSON from Azure Function

        Raises:
            requests.RequestException: If all retries fail
            ValueError: If base URL not configured
        """
        if not self.base_url:
            raise ValueError(
                "AZURE_FUNCTION_BASE_URL not configured. Set environment variable or check settings."
            )

        # Construct endpoint URL
        endpoint = f"{self.base_url}/{category}/{action}"

        logger.info(f"🚀 Triggering Azure Function: {endpoint}")
        logger.debug(f"📦 Payload: {payload}")

        try:
            response = requests.post(
                endpoint,
                json=payload,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )

            # Raise for HTTP errors
            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Azure Function triggered successfully: {result.get('status')}")

            return result

        except requests.Timeout as e:
            logger.error(f"⏱️ Request timeout after {timeout}s: {endpoint}")
            raise

        except requests.HTTPError as e:
            logger.error(
                f"❌ HTTP error {e.response.status_code}: {e.response.text}"
            )
            raise

        except requests.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            raise

        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            raise

    def trigger_with_execution_id(
        self,
        category: str,
        action: str,
        execution_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger function with execution ID and optional parameters.

        Convenience method for standard async tool workflow.

        Args:
            category: Tool category
            action: Action to perform
            execution_id: ToolExecution UUID
            parameters: Optional tool-specific parameters

        Returns:
            Response JSON from Azure Function
        """
        payload = {
            "executionId": execution_id,
            "parameters": parameters or {},
        }

        return self.trigger_function(category, action, payload)
