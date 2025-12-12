"""
Core views for MagicToolbox including health checks and home page.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render, redirect

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
    
    # Get statistics if user is staff
    stats = {}
    if request.user.is_authenticated and request.user.is_staff:
        from apps.tools.models import ToolExecution
        stats = {
            'total_executions': ToolExecution.objects.count(),
            'pending_executions': ToolExecution.objects.filter(status='pending').count(),
            'processing_executions': ToolExecution.objects.filter(status='processing').count(),
            'completed_executions': ToolExecution.objects.filter(status='completed').count(),
            'failed_executions': ToolExecution.objects.filter(status='failed').count(),
        }
    
    context = {
        'azure_function_base_url': azure_function_base_url,
        'endpoints_available': bool(azure_function_base_url),
        'stats': stats,
    }
    
    return render(request, "troubleshooting.html", context)


@user_passes_test(lambda u: u.is_staff)
def cleanup_all_data(request):
    """
    Admin-only endpoint to cleanup all conversion data.
    
    Deletes:
    - All blobs in uploads, processed, and video-uploads containers
    - All ToolExecution records from database
    
    Requires staff/admin privileges.
    """
    if request.method != 'POST':
        messages.error(request, 'Invalid request method')
        return redirect('core:troubleshooting')
    
    try:
        from apps.tools.models import ToolExecution
        from azure.storage.blob import BlobServiceClient
        from azure.identity import DefaultAzureCredential
        
        cleanup_stats = {
            'blobs_deleted': 0,
            'containers_checked': [],
            'database_records_deleted': 0,
            'errors': []
        }
        
        # Get blob service client
        connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
        
        if connection_string and "127.0.0.1" in connection_string:
            logger.info("🔧 Using local Azurite for cleanup")
            blob_service = BlobServiceClient.from_connection_string(connection_string)
        else:
            storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None) or getattr(settings, "AZURE_ACCOUNT_NAME", None)
            if not storage_account_name:
                raise Exception("Storage account not configured")
            
            logger.info(f"🔐 Using Azure Managed Identity for cleanup: {storage_account_name}")
            account_url = f"https://{storage_account_name}.blob.core.windows.net"
            credential = DefaultAzureCredential()
            blob_service = BlobServiceClient(account_url=account_url, credential=credential)
        
        # Containers to clean
        containers = ['uploads', 'processed', 'video-uploads']
        
        # Delete all blobs in each container
        for container_name in containers:
            try:
                cleanup_stats['containers_checked'].append(container_name)
                container_client = blob_service.get_container_client(container_name)
                
                # Check if container exists
                if not container_client.exists():
                    logger.warning(f"Container {container_name} does not exist, skipping")
                    continue
                
                # List and delete all blobs
                blobs = list(container_client.list_blobs())
                for blob in blobs:
                    try:
                        container_client.delete_blob(blob.name)
                        cleanup_stats['blobs_deleted'] += 1
                        logger.info(f"Deleted blob: {container_name}/{blob.name}")
                    except Exception as blob_error:
                        error_msg = f"Failed to delete blob {container_name}/{blob.name}: {str(blob_error)}"
                        logger.error(error_msg)
                        cleanup_stats['errors'].append(error_msg)
                
                logger.info(f"Cleaned container {container_name}: deleted {len(blobs)} blobs")
                
            except Exception as container_error:
                error_msg = f"Error accessing container {container_name}: {str(container_error)}"
                logger.error(error_msg)
                cleanup_stats['errors'].append(error_msg)
        
        # Delete all database records
        try:
            deleted_count = ToolExecution.objects.all().delete()[0]
            cleanup_stats['database_records_deleted'] = deleted_count
            logger.info(f"Deleted {deleted_count} database records")
        except Exception as db_error:
            error_msg = f"Failed to delete database records: {str(db_error)}"
            logger.error(error_msg)
            cleanup_stats['errors'].append(error_msg)
        
        # Display results
        if cleanup_stats['errors']:
            messages.warning(
                request,
                f"Cleanup completed with errors. "
                f"Deleted {cleanup_stats['blobs_deleted']} blobs and {cleanup_stats['database_records_deleted']} database records. "
                f"Errors: {len(cleanup_stats['errors'])}"
            )
        else:
            messages.success(
                request,
                f"✅ Cleanup successful! "
                f"Deleted {cleanup_stats['blobs_deleted']} blobs from {len(cleanup_stats['containers_checked'])} containers "
                f"and {cleanup_stats['database_records_deleted']} database records."
            )
        
        logger.info(f"Cleanup stats: {cleanup_stats}")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        messages.error(request, f"Cleanup failed: {str(e)}")
    
    return redirect('core:troubleshooting')
