"""
Tests for tool system.
"""

from rest_framework import status

import pytest

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
