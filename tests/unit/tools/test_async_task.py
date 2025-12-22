"""
Unit tests for AsyncTaskTrigger.

Tests Azure Function triggering with mocked HTTP requests.
"""

import pytest
from unittest.mock import Mock, patch
import requests

from apps.tools.services.async_task import AsyncTaskTrigger


class TestAsyncTaskTrigger:
    """Test suite for AsyncTaskTrigger."""
    
    def test_init_with_base_url(self):
        """Test initialization with base URL from settings."""
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            assert trigger.base_url == "https://func.azurewebsites.net/api"
    
    def test_init_without_base_url_logs_warning(self, caplog):
        """Test initialization without base URL logs warning."""
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = ""
            
            trigger = AsyncTaskTrigger()
            assert "not configured" in caplog.text
    
    @patch('apps.tools.services.async_task.requests.post')
    def test_trigger_function_success(self, mock_post):
        """Test successful function trigger."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "executionId": "123"}
        mock_post.return_value = mock_response
        
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            result = trigger.trigger_function(
                category="video",
                action="rotate",
                payload={"executionId": "123", "angle": 90}
            )
            
            assert result == {"status": "success", "executionId": "123"}
            mock_post.assert_called_once()
            
            # Verify correct endpoint
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://func.azurewebsites.net/api/video/rotate"
    
    @patch('apps.tools.services.async_task.requests.post')
    def test_trigger_function_with_timeout(self, mock_post):
        """Test function trigger respects timeout parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            trigger.trigger_function(
                category="pdf",
                action="convert",
                payload={"executionId": "456"},
                timeout=60
            )
            
            # Verify timeout was passed
            call_args = mock_post.call_args
            assert call_args[1]["timeout"] == 60
    
    def test_trigger_function_raises_without_base_url(self):
        """Test that trigger_function raises ValueError without base URL."""
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = ""
            
            trigger = AsyncTaskTrigger()
            
            with pytest.raises(ValueError, match="AZURE_FUNCTION_BASE_URL not configured"):
                trigger.trigger_function("video", "rotate", {})
    
    @patch('apps.tools.services.async_task.requests.post')
    def test_trigger_function_handles_http_error(self, mock_post):
        """Test that trigger_function handles HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_post.return_value = mock_response
        
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            
            with pytest.raises(requests.HTTPError):
                trigger.trigger_function("video", "rotate", {})
    
    @patch('apps.tools.services.async_task.requests.post')
    def test_trigger_function_handles_timeout(self, mock_post):
        """Test that trigger_function handles request timeout."""
        mock_post.side_effect = requests.Timeout("Request timeout")
        
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            
            with pytest.raises(requests.Timeout):
                trigger.trigger_function("video", "rotate", {})
    
    @patch('apps.tools.services.async_task.requests.post')
    def test_trigger_function_handles_connection_error(self, mock_post):
        """Test that trigger_function handles connection errors."""
        mock_post.side_effect = requests.ConnectionError("Connection failed")
        
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            
            with pytest.raises(requests.ConnectionError):
                trigger.trigger_function("video", "rotate", {})
    
    @patch('apps.tools.services.async_task.requests.post')
    def test_trigger_with_execution_id_convenience_method(self, mock_post):
        """Test trigger_with_execution_id convenience method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            result = trigger.trigger_with_execution_id(
                category="pdf",
                action="convert",
                execution_id="exec-123",
                parameters={"format": "docx"}
            )
            
            assert result["status"] == "success"
            
            # Verify payload structure
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["executionId"] == "exec-123"
            assert payload["parameters"] == {"format": "docx"}
    
    @patch('apps.tools.services.async_task.requests.post')
    def test_trigger_function_sets_correct_headers(self, mock_post):
        """Test that trigger_function sets correct HTTP headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            trigger.trigger_function("video", "rotate", {"executionId": "123"})
            
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            assert headers["Content-Type"] == "application/json"
    
    @patch('apps.tools.services.async_task.requests.post')
    def test_trigger_function_retries_on_failure(self, mock_post):
        """Test that trigger_function retries on transient failures."""
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = requests.RequestException()
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"status": "success"}
        
        mock_post.side_effect = [
            requests.RequestException("Transient error"),
            mock_response_success
        ]
        
        with patch('apps.tools.services.async_task.settings') as mock_settings:
            mock_settings.AZURE_FUNCTION_BASE_URL = "https://func.azurewebsites.net/api"
            
            trigger = AsyncTaskTrigger()
            result = trigger.trigger_function("video", "rotate", {"executionId": "123"})
            
            # Should succeed after retry
            assert result["status"] == "success"
            assert mock_post.call_count == 2
