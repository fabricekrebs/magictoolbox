"""
Core views for MagicToolbox including health checks and home page.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def home(request):
    """
    Home page view.
    """
    return render(request, "home.html")


def health_check(request):
    """
    Basic health check endpoint.

    Returns 200 OK if the application is running.
    Used by Azure Container Apps health probes.
    """
    return JsonResponse({"status": "healthy"}, status=200)


def readiness_check(request):
    """
    Readiness check endpoint that verifies critical services.

    Checks database and cache connectivity before reporting ready.
    Used by Azure Container Apps readiness probes.
    """
    checks = {
        "database": False,
        "cache": False,
    }

    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check cache connection
    try:
        cache.set("health_check", "ok", 10)
        checks["cache"] = cache.get("health_check") == "ok"
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")

    # Return 200 if all checks pass, 503 otherwise
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JsonResponse(
        {"status": "ready" if all_healthy else "not_ready", "checks": checks}, status=status_code
    )


def troubleshooting(request):
    """
    Troubleshooting page showing available diagnostic endpoints.
    
    Lists all Azure Function diagnostic endpoints for health checks,
    storage verification, and debugging.
    """
    azure_function_base_url = getattr(settings, 'AZURE_FUNCTION_BASE_URL', None)
    
    context = {
        'azure_function_base_url': azure_function_base_url,
        'endpoints_available': bool(azure_function_base_url),
    }
    
    return render(request, "troubleshooting.html", context)
