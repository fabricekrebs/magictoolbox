"""
Pytest fixtures for testing.

Provides reusable test fixtures for authentication, users, and API clients.
Also provides automatic mocking of Azure services for unit tests.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

import pytest
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ============================================================================
# Azure Service Mocks (auto-applied to all tests except azure_integration)
# ============================================================================


@pytest.fixture(autouse=True)
def mock_azure_storage(request, monkeypatch):
    """
    Automatically mock Azure Blob Storage for all tests except azure_integration tests.

    This prevents tests from trying to connect to real Azure storage.
    """
    # Skip mocking for tests marked with azure_integration
    if "azure_integration" in [marker.name for marker in request.node.iter_markers()]:
        yield
        return

    # Mock BlobServiceClient across all modules
    mock_blob_service = MagicMock()
    mock_container = MagicMock()
    mock_blob_client = MagicMock()

    # Setup mock chain
    mock_blob_service.get_container_client.return_value = mock_container
    mock_container.get_blob_client.return_value = mock_blob_client
    mock_blob_client.upload_blob.return_value = None
    mock_blob_client.download_blob.return_value.readall.return_value = b"mock data"

    # Apply mocks to all tool modules
    with patch(
        "apps.tools.plugins.pdf_docx_converter.BlobServiceClient",
        return_value=mock_blob_service,
    ):
        with patch(
            "apps.tools.plugins.video_rotation.BlobServiceClient",
            return_value=mock_blob_service,
        ):
            with patch(
                "apps.tools.plugins.ocr_tool.BlobServiceClient",
                return_value=mock_blob_service,
            ):
                with patch(
                    "apps.tools.plugins.gpx_merger.BlobServiceClient",
                    return_value=mock_blob_service,
                ):
                    yield mock_blob_service


@pytest.fixture(autouse=True)
def mock_azure_credentials(request):
    """
    Mock Azure credentials to prevent authentication attempts in unit tests.
    """
    # Skip mocking for tests marked with azure_integration
    if "azure_integration" in [marker.name for marker in request.node.iter_markers()]:
        yield
        return

    # Mock DefaultAzureCredential
    mock_cred = MagicMock()

    with patch(
        "apps.tools.plugins.pdf_docx_converter.DefaultAzureCredential", return_value=mock_cred
    ):
        with patch(
            "apps.tools.plugins.video_rotation.DefaultAzureCredential", return_value=mock_cred
        ):
            with patch(
                "apps.tools.plugins.ocr_tool.DefaultAzureCredential", return_value=mock_cred
            ):
                with patch(
                    "apps.tools.plugins.gpx_merger.DefaultAzureCredential", return_value=mock_cred
                ):
                    yield mock_cred


@pytest.fixture(autouse=True)
def mock_requests_for_azure_functions(request):
    """
    Mock requests library to prevent HTTP calls to Azure Functions in unit tests.
    """
    # Skip mocking for tests marked with azure_integration
    if "azure_integration" in [marker.name for marker in request.node.iter_markers()]:
        yield
        return

    # Mock requests.post
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}

    with patch("requests.post", return_value=mock_response) as mock_post:
        yield mock_post


# ============================================================================
# Authentication & User Fixtures
# ============================================================================


@pytest.fixture
def api_client():
    """Provide APIClient instance for testing."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="adminpass123"
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Provide APIClient authenticated with test user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Provide APIClient authenticated with admin user."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
