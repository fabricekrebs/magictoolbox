"""
URL configuration for API v1.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tools.views import ToolViewSet, ToolExecutionViewSet

app_name = "v1"

# Create router for ViewSets
router = DefaultRouter()
router.register(r"tools", ToolViewSet, basename="tool")
router.register(r"executions", ToolExecutionViewSet, basename="execution")

urlpatterns = [
    # Authentication endpoints
    path("auth/", include("apps.authentication.urls", namespace="auth")),
    # Tool endpoints
    path("", include(router.urls)),
]
