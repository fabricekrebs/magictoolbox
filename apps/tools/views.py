"""
Views for tool operations (both web UI and API endpoints).
"""

import logging
from pathlib import Path

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ToolExecution
from .registry import tool_registry
from .serializers import (
    ToolExecutionListSerializer,
    ToolExecutionSerializer,
    ToolMetadataSerializer,
    ToolProcessRequestSerializer,
    ToolProcessResponseSerializer,
)
from .tasks import process_tool_async

logger = logging.getLogger(__name__)


# Helper function for Azure Blob Storage authentication
def get_blob_service_client():
    """
    Get Azure Blob Storage client.
    
    Uses connection string for local Azurite, DefaultAzureCredential for Azure.
    This matches the pattern used in PDF and video converter plugins.
    """
    from django.conf import settings
    from azure.storage.blob import BlobServiceClient
    from azure.identity import DefaultAzureCredential
    
    connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

    # Check for local development (Azurite)
    if connection_string and "127.0.0.1" in connection_string:
        logger.info("🔧 Using local Azurite for blob storage")
        return BlobServiceClient.from_connection_string(connection_string)

    # Production: Use Managed Identity / DefaultAzureCredential
    storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None) or getattr(settings, "AZURE_ACCOUNT_NAME", None)
    if not storage_account_name:
        logger.error("❌ Storage account name not configured")
        raise Exception(
            "AZURE_STORAGE_ACCOUNT_NAME or AZURE_ACCOUNT_NAME not configured for production environment"
        )

    logger.info(f"🔐 Using Azure Managed Identity for storage account: {storage_account_name}")
    account_url = f"https://{storage_account_name}.blob.core.windows.net"
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=account_url, credential=credential)


# Template Views
def tool_list(request):
    """
    Display list of available tools.
    """
    tools = tool_registry.list_tools()
    return render(request, "tools/tool_list.html", {"tools": tools})


@login_required
def tool_detail(request, tool_slug):
    """
    Display tool detail and processing interface.
    Requires authentication. Handles both GET (display form) and POST (process file).
    """
    tool_instance = tool_registry.get_tool_instance(tool_slug)
    if not tool_instance:
        return render(request, "errors/404.html", status=404)

    metadata = tool_instance.get_metadata()

    # Create a dynamic form based on tool requirements
    class ToolForm(forms.Form):
        file = forms.FileField(
            label="Upload File",
            help_text=f"Maximum file size: {metadata.get('max_file_size', '50MB')}",
        )

    # Handle POST request - process the file
    if request.method == "POST":
        logger.info(f"POST request to {tool_slug}, FILES: {list(request.FILES.keys())}, POST: {list(request.POST.keys())}")
        form = ToolForm(request.POST, request.FILES)
        logger.info(f"Form valid: {form.is_valid()}, Has FILES: {bool(request.FILES)}")
        if form.is_valid() or request.FILES:  # Allow processing even if form validation fails if we have files
            try:
                # Support both 'file' and 'input_file' for flexibility
                uploaded_file = request.FILES.get('file') or request.FILES.get('input_file')
                logger.info(f"Uploaded file: {uploaded_file.name if uploaded_file else 'None'}")
                if not uploaded_file:
                    raise ValueError("No file uploaded")
                
                # Extract parameters from POST data
                parameters = {}
                for key, value in request.POST.items():
                    if key not in ['csrfmiddlewaretoken', 'file']:
                        parameters[key] = value
                
                # Validate the file using the tool
                is_valid, error_message = tool_instance.validate(uploaded_file, parameters)
                if not is_valid:
                    logger.warning(f"Validation failed for {tool_slug}: {error_message}")
                    messages.error(request, error_message or 'Invalid file')
                    context = {"tool": metadata, "form": form}
                    template_name = f'tools/{tool_slug.replace("-", "_")}.html'
                    try:
                        return render(request, template_name, context)
                    except Exception:
                        return render(request, "tools/tool_detail.html", context)
                
                # Create ToolExecution record
                import uuid
                execution_id = str(uuid.uuid4())
                
                logger.info(f"Creating ToolExecution for {tool_slug}, user={request.user.username}, file={uploaded_file.name}")
                
                execution = ToolExecution.objects.create(
                    id=execution_id,
                    user=request.user,
                    tool_name=tool_slug,
                    input_filename=uploaded_file.name,
                    input_size=uploaded_file.size,
                    parameters=parameters,
                    status="pending",
                )
                
                logger.info(f"Created ToolExecution {execution_id} successfully")
                
                # Process the file
                try:
                    output_filename, output_path = tool_instance.process(
                        uploaded_file, parameters, execution_id=execution_id
                    )
                    
                    # Update execution status
                    execution.status = "completed"
                    execution.output_filename = output_filename
                    execution.save()
                    
                    logger.info(f"File processed successfully for execution {execution_id}")
                    messages.success(request, f"File processed successfully: {output_filename}")
                    
                    # Re-render the form with success message
                    form = ToolForm()
                    context = {"tool": metadata, "form": form, "execution": execution}
                    template_name = f'tools/{tool_slug.replace("-", "_")}.html'
                    try:
                        return render(request, template_name, context)
                    except Exception:
                        return render(request, "tools/tool_detail.html", context)
                    
                except Exception as process_error:
                    logger.error(f"Error processing file with {tool_slug}: {process_error}", exc_info=True)
                    execution.status = "failed"
                    execution.error_message = str(process_error)
                    execution.save()
                    messages.error(request, f"Error processing file: {str(process_error)}")
                
            except Exception as e:
                logger.error(f"Error in tool_detail POST for {tool_slug}: {e}", exc_info=True)
                messages.error(request, f"Error: {str(e)}")
        else:
            logger.warning(f"Invalid form submission for {tool_slug}")
            messages.error(request, "Invalid form submission")
    
    # Handle GET request - display the form
    else:
        form = ToolForm()

    context = {
        "tool": metadata,
        "form": form,
    }

    # Use tool-specific template if it exists
    template_name = f'tools/{tool_slug.replace("-", "_")}.html'
    try:
        return render(request, template_name, context)
    except Exception as e:
        # Fall back to generic template
        logger.warning(f"Error rendering {template_name}: {e}")
        return render(request, "tools/tool_detail.html", context)


@login_required
def my_conversions(request):
    """
    Display user's conversion history.
    Shows all PDF to DOCX conversions for the authenticated user.
    """
    # Get all conversions for the user, most recent first
    conversions = ToolExecution.objects.filter(
        user=request.user, tool_name="pdf-docx-converter"
    ).order_by("-created_at")

    # Calculate status counts
    total_count = conversions.count()
    completed_count = conversions.filter(status="completed").count()
    processing_count = conversions.filter(status="processing").count()
    pending_count = conversions.filter(status="pending").count()
    failed_count = conversions.filter(status="failed").count()

    context = {
        "conversions": conversions,
        "total_count": total_count,
        "completed_count": completed_count,
        "processing_count": processing_count,
        "pending_count": pending_count,
        "failed_count": failed_count,
    }

    return render(request, "tools/my_conversions.html", context)


@login_required
@require_http_methods(["POST"])
def delete_conversion(request, execution_id):
    """
    Delete a conversion and its associated files from storage.
    Only the owner can delete their own conversions.
    """
    from django.conf import settings
    from django.contrib import messages
    from django.http import JsonResponse
    from django.shortcuts import redirect

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    try:
        # Get execution and verify ownership
        execution = ToolExecution.objects.get(id=execution_id, user=request.user)

        # Delete blob from storage if it exists
        if execution.output_file:
            try:
                blob_name = execution.output_file.name

                # Initialize blob service client
                connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

                if connection_string and "127.0.0.1" in connection_string:
                    # Local Azurite
                    blob_service = BlobServiceClient.from_connection_string(connection_string)
                else:
                    # Production Azure
                    storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None)
                    if storage_account_name:
                        account_url = f"https://{storage_account_name}.blob.core.windows.net"
                        credential = DefaultAzureCredential()
                        blob_service = BlobServiceClient(
                            account_url=account_url, credential=credential
                        )
                    else:
                        blob_service = None

                if blob_service:
                    # Delete from processed container
                    blob_client = blob_service.get_blob_client(
                        container="processed", blob=blob_name
                    )
                    if blob_client.exists():
                        blob_client.delete_blob()
                        logger.info(f"Deleted blob: {blob_name}")

                    # Also try to delete from uploads container if it exists
                    upload_blob_name = f"pdf/{execution.id}.pdf"
                    upload_blob_client = blob_service.get_blob_client(
                        container="uploads", blob=upload_blob_name
                    )
                    if upload_blob_client.exists():
                        upload_blob_client.delete_blob()
                        logger.info(f"Deleted upload blob: {upload_blob_name}")

            except Exception as e:
                logger.warning(f"Failed to delete blob for execution {execution_id}: {e}")

        # Delete the execution record
        input_filename = execution.input_filename
        execution.delete()

        logger.info(f"Deleted conversion {execution_id} for user {request.user.email}")

        # Return JSON response for AJAX requests
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": True, "message": f"Deleted conversion for {input_filename}"}
            )

        # Redirect with success message for regular requests
        messages.success(request, f"Successfully deleted conversion for {input_filename}")
        return redirect("tools:my_conversions")

    except ToolExecution.DoesNotExist:
        logger.warning(
            f"Conversion {execution_id} not found or user {request.user.email} not authorized"
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": "Conversion not found"}, status=404)

        messages.error(request, "Conversion not found")
        return redirect("tools:my_conversions")

    except Exception as e:
        logger.error(f"Failed to delete conversion {execution_id}: {e}", exc_info=True)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": str(e)}, status=500)

        messages.error(request, f"Failed to delete conversion: {str(e)}")
        return redirect("tools:my_conversions")


@login_required
@require_http_methods(["POST"])
def delete_all_conversions(request):
    """
    Delete all conversions and their associated files from storage.
    Only deletes the authenticated user's own conversions.
    """
    from django.conf import settings
    from django.contrib import messages
    from django.http import JsonResponse
    from django.shortcuts import redirect

    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    try:
        # Get all conversions for the user
        conversions = ToolExecution.objects.filter(
            user=request.user, tool_name="pdf-docx-converter"
        )

        total_count = conversions.count()

        if total_count == 0:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "message": "No conversions to delete"})
            messages.info(request, "No conversions to delete")
            return redirect("tools:my_conversions")

        # Initialize blob service client
        connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)
        blob_service = None

        if connection_string and "127.0.0.1" in connection_string:
            # Local Azurite
            blob_service = BlobServiceClient.from_connection_string(connection_string)
        else:
            # Production Azure
            storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None)
            if storage_account_name:
                account_url = f"https://{storage_account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                blob_service = BlobServiceClient(account_url=account_url, credential=credential)

        deleted_count = 0
        failed_count = 0

        # Delete each conversion
        for execution in conversions:
            try:
                # Delete blobs from storage
                if blob_service:
                    # Delete processed file
                    if execution.output_file and execution.output_file.name:
                        blob_name = execution.output_file.name
                    else:
                        blob_name = f"docx/{execution.id}.docx"

                    try:
                        blob_client = blob_service.get_blob_client(
                            container="processed", blob=blob_name
                        )
                        if blob_client.exists():
                            blob_client.delete_blob()
                    except Exception as e:
                        logger.warning(f"Failed to delete blob {blob_name}: {e}")

                    # Delete upload file
                    try:
                        upload_blob_name = f"pdf/{execution.id}.pdf"
                        upload_blob_client = blob_service.get_blob_client(
                            container="uploads", blob=upload_blob_name
                        )
                        if upload_blob_client.exists():
                            upload_blob_client.delete_blob()
                    except Exception as e:
                        logger.warning(f"Failed to delete upload blob for {execution.id}: {e}")

                # Delete database record
                execution.delete()
                deleted_count += 1

            except Exception as e:
                logger.error(f"Failed to delete conversion {execution.id}: {e}")
                failed_count += 1

        logger.info(f"Bulk deleted {deleted_count} conversions for user {request.user.email}")

        # Return response
        message = f"Successfully deleted {deleted_count} conversion(s)"
        if failed_count > 0:
            message += f" ({failed_count} failed)"

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "message": message,
                    "deletedCount": deleted_count,
                    "failedCount": failed_count,
                }
            )

        messages.success(request, message)
        return redirect("tools:my_conversions")

    except Exception as e:
        logger.error(f"Failed to bulk delete conversions: {e}", exc_info=True)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": str(e)}, status=500)

        messages.error(request, f"Failed to delete conversions: {str(e)}")
        return redirect("tools:my_conversions")


class ToolViewSet(viewsets.ViewSet):
    """
    ViewSet for tool operations.

    Provides endpoints for:
    - Listing available tools
    - Processing files with tools
    """

    permission_classes = [IsAuthenticated]  # Require authentication

    def list(self, request):
        """
        List all available tools with metadata.

        GET /api/v1/tools/
        """
        tools = tool_registry.list_tools()
        serializer = ToolMetadataSerializer(tools, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        Get metadata for a specific tool.

        GET /api/v1/tools/{tool_name}/
        """
        tool_instance = tool_registry.get_tool_instance(pk)
        if not tool_instance:
            return Response(
                {"error": {"message": f"Tool '{pk}' not found", "code": "tool_not_found"}},
                status=status.HTTP_404_NOT_FOUND,
            )

        metadata = tool_instance.get_metadata()
        serializer = ToolMetadataSerializer(metadata)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="convert")
    def convert_file(self, request, pk=None):
        """
        Synchronous file conversion endpoint with bulk upload support.

        POST /api/v1/tools/{tool_name}/convert/

        For image-format-converter:
        - file or files[]: Image file(s) to convert (single or multiple)
        - output_format: Target format (jpg, png, webp, etc.)
        - quality: Quality 1-100 (optional)
        - width: Target width in pixels (optional)
        - height: Target height in pixels (optional)

        For gpx-kml-converter:
        - file: GPS file to convert
        - conversion_type: gpx_to_kml or kml_to_gpx (optional, auto-detected)
        - name: Document name (optional)
        """
        import io
        import zipfile

        from django.http import HttpResponse

        tool_instance = tool_registry.get_tool_instance(pk)
        if not tool_instance:
            return Response({"error": "Tool not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if tool requires file upload
        requires_file = getattr(tool_instance, "requires_file_upload", True)

        # Handle tools that don't require file upload (e.g., unit converter)
        if not requires_file:
            # Get all parameters from request body (JSON)
            import json

            try:
                if request.content_type == "application/json":
                    parameters = json.loads(request.body)
                else:
                    parameters = dict(request.data)
            except Exception as e:
                return Response(
                    {"error": f"Invalid request data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Validate parameters
            is_valid, error_msg = tool_instance.validate(input_file=None, parameters=parameters)
            if not is_valid:
                return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

            # Process without file
            try:
                result_dict, result_string = tool_instance.process(
                    input_file=None, parameters=parameters
                )
                return Response(result_dict)
            except Exception as e:
                logger.error(f"Tool processing failed: {e}", exc_info=True)
                return Response(
                    {"error": f"Processing failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        # Handle both single file and multiple files
        files = request.FILES.getlist("files[]") or request.FILES.getlist("files")
        if not files:
            # Try single file upload
            single_file = request.FILES.get("file")
            if single_file:
                files = [single_file]

        if not files:
            return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Get parameters from request - handle different tool types
        parameters = {}

        # Image converter parameters
        if request.data.get("output_format"):
            parameters["output_format"] = request.data.get("output_format")
        if request.data.get("quality"):
            parameters["quality"] = request.data.get("quality")
        if request.data.get("width"):
            parameters["width"] = request.data.get("width")
        if request.data.get("height"):
            parameters["height"] = request.data.get("height")

        # GPX/KML converter parameters
        if request.data.get("conversion_type"):
            parameters["conversion_type"] = request.data.get("conversion_type")
        if request.data.get("name"):
            parameters["name"] = request.data.get("name")

        # GPX Speed Modifier parameters
        if request.data.get("mode"):
            parameters["mode"] = request.data.get("mode")
        if request.data.get("speed_multiplier"):
            parameters["speed_multiplier"] = request.data.get("speed_multiplier")

        # PDF to DOCX converter parameters
        if request.data.get("start_page"):
            parameters["start_page"] = request.data.get("start_page")
        if request.data.get("end_page"):
            parameters["end_page"] = request.data.get("end_page")

        # Video rotation parameters
        if request.data.get("rotation"):
            parameters["rotation"] = request.data.get("rotation")

        # Special handling for async tools (PDF converter, Video rotation, Image converter, GPX tools)
        if pk in ["pdf-docx-converter", "video-rotation", "image-format-converter", "gpx-kml-converter", "gpx-speed-modifier"]:
            # Handle single file upload for async processing
            if len(files) == 1:
                file = files[0]
                is_valid, error_msg = tool_instance.validate(file, parameters)
                if not is_valid:
                    return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    # Generate execution ID first
                    import uuid
                    import requests
                    from django.conf import settings
                    execution_id = str(uuid.uuid4())
                    
                    # Create ToolExecution record BEFORE processing
                    # Determine container prefix based on tool type
                    container_prefixes = {
                        "pdf-docx-converter": "uploads/pdf",
                        "video-rotation": "video-uploads/video",
                        "image-format-converter": "uploads/image",
                        "gpx-kml-converter": "uploads/gpx",
                        "gpx-speed-modifier": "uploads/gpx",
                    }
                    container_prefix = container_prefixes.get(pk, "uploads")
                    file_ext = Path(file.name).suffix
                    
                    _execution = ToolExecution.objects.create(
                        id=execution_id,
                        user=request.user,
                        tool_name=pk,
                        input_filename=file.name,
                        input_size=file.size,
                        parameters=parameters,
                        status="pending",
                        azure_function_invoked=True,
                        function_execution_id=execution_id,
                        input_blob_path=f"{container_prefix}/{execution_id}{file_ext}",
                    )
                    
                    # Now process with the pre-created execution ID (uploads to blob)
                    returned_execution_id, _ = tool_instance.process(file, parameters, execution_id=execution_id)

                    # For video rotation, trigger Azure Function immediately
                    if pk == "video-rotation":
                        function_url = getattr(settings, 'AZURE_FUNCTION_URL', None)
                        if function_url:
                            try:
                                rotation_endpoint = f"{function_url.rstrip('/')}/api/video/rotate"
                                payload = {
                                    "execution_id": execution_id,
                                    "blob_name": f"video-uploads/video/{execution_id}{file_ext}",
                                    "rotation": parameters.get("rotation")
                                }
                                logger.info(f"Triggering video rotation: {rotation_endpoint}")
                                response = requests.post(rotation_endpoint, json=payload, timeout=10)
                                logger.info(f"Azure Function response: {response.status_code}")
                            except Exception as func_error:
                                logger.warning(f"Failed to trigger Azure Function: {func_error}")

                    return Response(
                        {
                            "executionId": execution_id,
                            "filename": file.name,
                            "status": "pending",
                            "statusUrl": f"/api/v1/executions/{execution_id}/status/",
                            "message": "File uploaded for processing",
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )

                except Exception as e:
                    logger.error(f"Processing failed: {e}", exc_info=True)
                    return Response(
                        {"error": f"Processing failed: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

        # Special handling for PDF to DOCX converter (Azure Functions only) - batch processing
        if pk == "pdf-docx-converter":
            # Check if tool has process_multiple method for batch processing
            if hasattr(tool_instance, "process_multiple") and len(files) > 1:
                # Validate all files
                for file in files:
                    is_valid, error_msg = tool_instance.validate(file, parameters)
                    if not is_valid:
                        return Response(
                            {"error": f"File '{file.name}' validation failed: {error_msg}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                # Process all files and get execution IDs
                try:
                    results = tool_instance.process_multiple(files, parameters)

                    # Create ToolExecution records for all files
                    executions = []
                    for execution_id, original_filename in results:
                        # Find the corresponding file for size
                        file_size = next((f.size for f in files if f.name == original_filename), 0)

                        _execution = ToolExecution.objects.create(
                            id=execution_id,
                            user=request.user,
                            tool_name=pk,
                            input_filename=original_filename,
                            input_size=file_size,
                            parameters=parameters,
                            status="pending",
                            azure_function_invoked=True,
                            function_execution_id=execution_id,
                            input_blob_path=f"uploads/pdf/{execution_id}.pdf",
                        )
                        executions.append(
                            {
                                "executionId": execution_id,
                                "filename": original_filename,
                                "status": "pending",
                            }
                        )

                    return Response(
                        {
                            "message": f"{len(files)} files uploaded for processing",
                            "executions": executions,
                            "batchStatusUrl": "/api/v1/executions/batch-status/",
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )

                except Exception as e:
                    logger.error(f"Batch PDF processing failed: {e}", exc_info=True)
                    return Response(
                        {"error": f"Batch processing failed: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            # Single file PDF processing (Azure Functions)
            elif len(files) == 1:
                file = files[0]
                is_valid, error_msg = tool_instance.validate(file, parameters)
                if not is_valid:
                    return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

                try:
                    # Generate execution ID first
                    import uuid
                    execution_id = str(uuid.uuid4())
                    
                    # Create ToolExecution record BEFORE processing
                    # This ensures it exists when the Azure Function response handler tries to update it
                    _execution = ToolExecution.objects.create(
                        id=execution_id,
                        user=request.user,
                        tool_name=pk,
                        input_filename=file.name,
                        input_size=file.size,
                        parameters=parameters,
                        status="pending",
                        azure_function_invoked=True,
                        function_execution_id=execution_id,
                        input_blob_path=f"uploads/pdf/{execution_id}.pdf",
                    )
                    
                    # Now process with the pre-created execution ID
                    returned_execution_id, _ = tool_instance.process(file, parameters, execution_id=execution_id)

                    return Response(
                        {
                            "executionId": execution_id,
                            "filename": file.name,
                            "status": "pending",
                            "statusUrl": f"/api/v1/executions/{execution_id}/status/",
                            "message": "File uploaded for processing",
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )

                except Exception as e:
                    logger.error(f"PDF processing failed: {e}", exc_info=True)
                    return Response(
                        {"error": f"Processing failed: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

        # Process multiple files (for other tools - returns ZIP)
        if len(files) > 1:
            # Create a ZIP file with all converted images
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file in files:
                    # Validate
                    is_valid, error_msg = tool_instance.validate(file, parameters)
                    if not is_valid:
                        logger.warning(f"Skipping {file.name}: {error_msg}")
                        continue

                    try:
                        # Process
                        output_path, output_filename = tool_instance.process(file, parameters)

                        # Add to ZIP
                        with open(output_path, "rb") as f:
                            zip_file.writestr(output_filename, f.read())

                        # Cleanup
                        tool_instance.cleanup(output_path)

                    except Exception as e:
                        logger.error(f"Failed to convert {file.name}: {e}")
                        continue

            # Return ZIP file
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
            response["Content-Disposition"] = 'attachment; filename="converted_images.zip"'
            return response

        else:
            # Single file conversion
            file = files[0]

            # Validate
            is_valid, error_msg = tool_instance.validate(file, parameters)
            if not is_valid:
                return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Process (sync or async depending on tool configuration)
                output_path, output_filename = tool_instance.process(file, parameters)

                # Check if async processing (Azure Functions)
                if output_filename is None:
                    # Async processing - output_path is actually execution_id
                    execution_id = output_path

                    # Create ToolExecution record for tracking with Azure Functions fields
                    _execution = ToolExecution.objects.create(
                        id=execution_id,
                        user=request.user,
                        tool_name=pk,
                        input_filename=file.name,
                        input_size=file.size,
                        parameters=parameters,
                        status="pending",
                        azure_function_invoked=True,
                        function_execution_id=execution_id,
                        input_blob_path=f"uploads/pdf/{execution_id}.pdf",
                    )

                    # Return 202 Accepted with execution ID
                    return Response(
                        {
                            "executionId": execution_id,
                            "status": "pending",
                            "message": "File uploaded for processing. Use the executionId to check status.",
                            "statusUrl": f"/api/v1/executions/{execution_id}/status/",
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )

                # Synchronous processing - handle the output file
                # Special handling for JSON responses (e.g., GPX analyze mode)
                file_ext = output_filename.split(".")[-1].lower()
                if file_ext == "json":
                    # Read JSON and return as JSON response
                    import json

                    with open(output_path, "r", encoding="utf-8") as f:
                        json_data = json.load(f)

                    # Cleanup
                    tool_instance.cleanup(output_path)

                    # Return JSON response
                    return Response(json_data)

                # Read the output file
                with open(output_path, "rb") as f:
                    output_data = f.read()

                # Cleanup
                tool_instance.cleanup(output_path)

                # Determine content type based on file extension
                content_type_map = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                    "gif": "image/gif",
                    "bmp": "image/bmp",
                    "tiff": "image/tiff",
                    "tif": "image/tiff",
                    "ico": "image/x-icon",
                    "svg": "image/svg+xml",
                    "gpx": "application/gpx+xml",
                    "kml": "application/vnd.google-earth.kml+xml",
                    "xml": "application/xml",
                    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "pdf": "application/pdf",
                    # Video formats
                    "mp4": "video/mp4",
                    "avi": "video/x-msvideo",
                    "mov": "video/quicktime",
                    "mkv": "video/x-matroska",
                    "webm": "video/webm",
                    "flv": "video/x-flv",
                    "wmv": "video/x-ms-wmv",
                    "m4v": "video/x-m4v",
                    "mpg": "video/mpeg",
                    "mpeg": "video/mpeg",
                    "3gp": "video/3gpp",
                }
                content_type = content_type_map.get(file_ext, "application/octet-stream")

                # Return the converted file
                response = HttpResponse(output_data, content_type=content_type)
                response["Content-Disposition"] = f'attachment; filename="{output_filename}"'
                return response

            except Exception as e:
                logger.error(f"Image conversion failed: {e}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="merge")
    def merge_files(self, request, pk=None):
        """
        Merge multiple GPX files into a single file.

        POST /api/v1/tools/{tool_name}/merge/

        For gpx-merger:
        - files[]: Multiple GPX files to merge (minimum 2)
        - merge_mode: chronological|sequential|preserve_order (optional, default: chronological)
        - output_name: Name for merged file without extension (optional, default: merged_track)
        """
        tool_instance = tool_registry.get_tool_instance(pk)
        if not tool_instance:
            return Response({"error": "Tool not found"}, status=status.HTTP_404_NOT_FOUND)

        # Only support tools with process_multiple method
        if not hasattr(tool_instance, "process_multiple"):
            return Response(
                {"error": "Tool does not support merging multiple files"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get files from request
        files = request.FILES.getlist("files[]") or request.FILES.getlist("files")
        if not files:
            return Response({"error": "No files provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Get merge parameters
        parameters = {
            "merge_mode": request.data.get("merge_mode", "chronological"),
            "output_name": request.data.get("output_name", "merged_track"),
        }

        # Validate using validate_multiple if available
        if hasattr(tool_instance, "validate_multiple"):
            is_valid, error_msg = tool_instance.validate_multiple(files, parameters)
            if not is_valid:
                return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Fallback: validate each file individually
            for file in files:
                is_valid, error_msg = tool_instance.validate(file, parameters)
                if not is_valid:
                    return Response(
                        {"error": f"File '{file.name}' validation failed: {error_msg}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Process files
        try:
            # Call process_multiple which returns list of (execution_id, filename) tuples
            results = tool_instance.process_multiple(files, parameters)

            # For merge operations, we expect a single result
            if results and len(results) > 0:
                execution_id, output_filename = results[0]

                # Create ToolExecution record
                total_size = sum(f.size for f in files)
                input_filenames = ", ".join(f.name for f in files)

                _execution = ToolExecution.objects.create(
                    id=execution_id,
                    user=request.user,
                    tool_name=pk,
                    input_filename=input_filenames,
                    output_filename=output_filename,
                    input_size=total_size,
                    parameters=parameters,
                    status="pending",
                    azure_function_invoked=True,
                    function_execution_id=execution_id,
                    input_blob_path=f"uploads/gpx/{execution_id}_*.gpx",
                )

                return Response(
                    {
                        "executions": [
                            {
                                "executionId": execution_id,
                                "filename": output_filename,
                                "status": "pending",
                                "statusUrl": f"/api/v1/executions/{execution_id}/status/",
                            }
                        ],
                        "message": f"{len(files)} files uploaded for merging",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                return Response(
                    {"error": "No results returned from merge operation"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(f"Merge failed: {e}", exc_info=True)
            return Response(
                {"error": f"Merge failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    def process(self, request):
        """
        Process a file with specified tool.

        POST /api/v1/tools/process/

        Request body:
        - toolName: Name of tool to use
        - file: File to process
        - parameters: Tool-specific parameters (optional)
        """
        serializer = ToolProcessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tool_name = serializer.validated_data["toolName"]
        file = serializer.validated_data["file"]
        parameters = serializer.validated_data.get("parameters", {})

        # Create execution record
        execution = ToolExecution.objects.create(
            user=request.user,
            tool_name=tool_name,
            input_filename=file.name,
            input_size=file.size,
            parameters=parameters,
            status="pending",
        )

        # Save input file
        execution.input_file = file
        execution.save()

        # Queue async processing
        process_tool_async.delay(
            execution_id=str(execution.id),
            tool_name=tool_name,
            input_file_path=execution.input_file.path,
            parameters=parameters,
        )

        response_data = {
            "executionId": str(execution.id),
            "status": "pending",
            "message": "Tool processing queued",
        }

        response_serializer = ToolProcessResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="upload-video")
    def upload_video(self, request, pk=None):
        """
        Upload a video file to blob storage without processing.
        
        POST /api/v1/tools/video-rotation/upload-video/
        
        Returns: {"video_id": "...", "filename": "...", "blob_url": "..."}
        """
        if pk != "video-rotation":
            return Response({"error": "This endpoint is only for video-rotation tool"}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        tool_instance = tool_registry.get_tool_instance(pk)
        if not tool_instance:
            return Response({"error": "Tool not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate file (only size and type, not rotation)
        # Check file size
        if file.size > tool_instance.max_file_size:
            return Response({"error": f"File size exceeds maximum of {tool_instance.max_file_size / (1024 * 1024):.0f}MB"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check file extension
        from pathlib import Path
        file_ext = Path(file.name).suffix.lower()
        if file_ext not in tool_instance.allowed_input_types:
            return Response({"error": f"Unsupported file type: {file_ext}. Allowed: {', '.join(tool_instance.allowed_input_types)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import uuid
            from pathlib import Path
            
            # Generate video ID
            video_id = str(uuid.uuid4())
            file_ext = Path(file.name).suffix
            blob_name = f"video/{video_id}{file_ext}"
            
            # Get blob service client using helper function
            blob_service = get_blob_service_client()
            
            # Upload to video-uploads container
            blob_client = blob_service.get_blob_client(container="video-uploads", blob=blob_name)
            
            metadata = {
                "user_id": str(request.user.id),
                "original_filename": file.name,
                "file_size": str(file.size),
                "uploaded_at": str(timezone.now()),
            }
            
            blob_client.upload_blob(file.read(), overwrite=True, metadata=metadata)
            
            logger.info(f"Video uploaded: {blob_name} by user {request.user.email}")
            
            return Response({
                "video_id": video_id,
                "filename": file.name,
                "blob_name": blob_name,
                "size": file.size,
                "message": "Video uploaded successfully"
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Video upload failed: {e}", exc_info=True)
            return Response({"error": f"Upload failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=["get"], url_path="list-videos")
    def list_videos(self, request, pk=None):
        """
        List all uploaded videos for the current user.
        
        GET /api/v1/tools/video-rotation/list-videos/
        
        Returns: [{"video_id": "...", "filename": "...", "size": ..., "uploaded_at": "..."}, ...]
        """
        if pk != "video-rotation":
            return Response({"error": "This endpoint is only for video-rotation tool"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from django.conf import settings
            # Get blob service client using helper function
            blob_service = get_blob_service_client()
            
            # List blobs in video-uploads container for this user
            container_client = blob_service.get_container_client("video-uploads")
            
            videos = []
            for blob in container_client.list_blobs(name_starts_with="video/"):
                # Get blob metadata
                blob_client = container_client.get_blob_client(blob.name)
                properties = blob_client.get_blob_properties()
                metadata = properties.metadata
                
                # Only include videos for this user
                if metadata.get("user_id") == str(request.user.id):
                    video_id = blob.name.split("/")[1].split(".")[0]  # Extract UUID from video/{uuid}.ext
                    videos.append({
                        "video_id": video_id,
                        "filename": metadata.get("original_filename", blob.name),
                        "size": blob.size,
                        "uploaded_at": metadata.get("uploaded_at"),
                        "blob_name": blob.name,
                    })
            
            return Response({"videos": videos}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to list videos: {e}", exc_info=True)
            return Response({"error": f"Failed to list videos: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=["post"], url_path="rotate-video")
    def rotate_video_from_blob(self, request, pk=None):
        """
        Rotate a video that's already uploaded to blob storage.
        
        POST /api/v1/tools/video-rotation/rotate-video/
        
        Body: {"video_id": "...", "rotation": "90_cw|90_ccw|180"}
        
        Returns: {"execution_id": "...", "status": "pending", ...}
        """
        if pk != "video-rotation":
            return Response({"error": "This endpoint is only for video-rotation tool"}, status=status.HTTP_400_BAD_REQUEST)
        
        video_id = request.data.get("video_id")
        rotation = request.data.get("rotation")
        
        if not video_id or not rotation:
            return Response({"error": "video_id and rotation are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import uuid
            import requests
            from django.conf import settings
            from pathlib import Path
            
            # Get blob service client using helper function
            blob_service = get_blob_service_client()
            
            # Find the blob
            container_client = blob_service.get_container_client("video-uploads")
            blob_name = None
            original_filename = None
            
            for blob in container_client.list_blobs(name_starts_with=f"video/{video_id}"):
                blob_client = container_client.get_blob_client(blob.name)
                properties = blob_client.get_blob_properties()
                metadata = properties.metadata
                
                # Verify user owns this video
                if metadata.get("user_id") == str(request.user.id):
                    blob_name = blob.name
                    original_filename = metadata.get("original_filename", blob.name)
                    break
            
            if not blob_name:
                return Response({"error": "Video not found or access denied"}, status=status.HTTP_404_NOT_FOUND)
            
            # Generate execution ID
            execution_id = str(uuid.uuid4())
            file_ext = Path(blob_name).suffix
            
            # Create ToolExecution record
            _execution = ToolExecution.objects.create(
                id=execution_id,
                user=request.user,
                tool_name=pk,
                input_filename=original_filename,
                input_size=0,  # Size already in blob
                parameters={"rotation": rotation},
                status="pending",
                azure_function_invoked=True,
                function_execution_id=execution_id,
                input_blob_path=blob_name,
            )
            
            # Trigger Azure Function
            base_url = getattr(settings, 'AZURE_FUNCTION_BASE_URL', None)
            if base_url:
                function_url = f"{base_url}/video/rotate"
                try:
                    # Convert rotation string to integer for Azure Function
                    rotation_map = {
                        "90_cw": 90,
                        "90_ccw": 270,
                        "180": 180
                    }
                    rotation_degrees = rotation_map.get(rotation, 90)
                    
                    # Fix blob_name to include container name
                    # blob_name format: "video/xxxxx.mp4" from video-uploads container
                    # Azure Function expects: "video-uploads/video/xxxxx.mp4"
                    full_blob_path = f"video-uploads/{blob_name}" if not blob_name.startswith("video-uploads/") else blob_name
                    
                    payload = {
                        "execution_id": execution_id,
                        "blob_name": full_blob_path,
                        "rotation": rotation_degrees
                    }
                    logger.info(f"🚀 Triggering video rotation (async): {function_url}")
                    logger.info(f"Payload: {payload}")
                    # Fire-and-forget: trigger the function without waiting for completion
                    # Frontend will poll status endpoint to check progress
                    response = requests.post(function_url, json=payload, timeout=5)
                    logger.info(f"✅ Azure Function triggered: {response.status_code}")
                except requests.exceptions.Timeout:
                    # Expected for async operations - function is processing in background
                    logger.info(f"⏱️ Azure Function processing asynchronously (timeout OK)")
                except Exception as func_error:
                    logger.error(f"❌ Failed to trigger Azure Function: {func_error}", exc_info=True)
            
            return Response({
                "execution_id": execution_id,
                "video_id": video_id,
                "filename": original_filename,
                "rotation": rotation,
                "status": "pending",
                "statusUrl": f"/api/v1/executions/{execution_id}/status/",
                "message": "Video rotation started"
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Failed to rotate video: {e}", exc_info=True)
            return Response({"error": f"Rotation failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ToolExecutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for tool execution history.

    Provides read access to execution records and delete capability.
    Only allows GET (list, retrieve) and DELETE operations.
    """

    permission_classes = [IsAuthenticated]  # Require authentication
    serializer_class = ToolExecutionSerializer
    http_method_names = ['get', 'delete', 'head', 'options']  # Restrict to GET and DELETE only

    def get_queryset(self):
        """Return executions for the authenticated user only, with optional filtering."""
        queryset = ToolExecution.objects.filter(user=self.request.user)
        
        # Apply query parameter filters
        tool_name = self.request.query_params.get('tool_name', None)
        status = self.request.query_params.get('status', None)
        
        if tool_name:
            queryset = queryset.filter(tool_name=tool_name)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete execution record and associated blob files.
        
        DELETE /api/v1/executions/{id}/
        
        Returns:
            204 No Content on success
            404 Not Found if execution doesn't exist
            403 Forbidden if user doesn't own the execution
        """
        try:
            execution = self.get_object()  # Automatically filters by user via get_queryset
            
            # Delete associated blob files from storage
            from azure.storage.blob import BlobServiceClient
            from azure.identity import DefaultAzureCredential
            from django.conf import settings
            import logging
            
            logger = logging.getLogger(__name__)
            
            try:
                # Get blob service client
                connection_string = getattr(settings, 'AZURE_STORAGE_CONNECTION_STRING', None)
                
                if connection_string and "127.0.0.1" in connection_string:
                    # Local development with Azurite
                    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                    logger.info("🔧 Using Azurite for blob deletion")
                else:
                    # Production with Managed Identity
                    storage_account_name = getattr(settings, 'AZURE_STORAGE_ACCOUNT_NAME', None)
                    if storage_account_name:
                        account_url = f"https://{storage_account_name}.blob.core.windows.net"
                        credential = DefaultAzureCredential()
                        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
                        logger.info("🔐 Using Managed Identity for blob deletion")
                    else:
                        logger.warning("⚠️ No storage configuration found, skipping blob deletion")
                        blob_service_client = None
                
                if blob_service_client:
                    # Delete input blob if exists
                    if execution.input_blob_path:
                        try:
                            container_name = execution.input_blob_path.split('/')[0]
                            blob_name = '/'.join(execution.input_blob_path.split('/')[1:])
                            blob_client = blob_service_client.get_blob_client(
                                container=container_name,
                                blob=blob_name
                            )
                            blob_client.delete_blob()
                            logger.info(f"✅ Deleted input blob: {execution.input_blob_path}")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to delete input blob: {e}")
                    
                    # Delete output blob if exists
                    if execution.output_blob_path:
                        try:
                            container_name = execution.output_blob_path.split('/')[0]
                            blob_name = '/'.join(execution.output_blob_path.split('/')[1:])
                            blob_client = blob_service_client.get_blob_client(
                                container=container_name,
                                blob=blob_name
                            )
                            blob_client.delete_blob()
                            logger.info(f"✅ Deleted output blob: {execution.output_blob_path}")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to delete output blob: {e}")
            
            except Exception as e:
                logger.error(f"❌ Error during blob deletion: {e}")
                # Continue with database deletion even if blob deletion fails
            
            # Delete the database record
            execution.delete()
            logger.info(f"✅ Deleted execution record: {execution.id}")
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except ToolExecution.DoesNotExist:
            return Response(
                {"error": "Execution not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def get_serializer_class(self):
        """Use simplified serializer for list view."""
        if self.action == "list":
            return ToolExecutionListSerializer
        return ToolExecutionSerializer

    @action(detail=False, methods=["post"], url_path="batch-status")
    def batch_status(self, request):
        """
        Check status of multiple conversions at once.

        POST /api/v1/tools/executions/batch-status/

        Request body:
        {
            "executionIds": ["uuid1", "uuid2", "uuid3"]
        }

        Returns:
        {
            "executions": [
                {
                    "executionId": "uuid1",
                    "status": "completed",
                    "filename": "doc1.pdf",
                    "outputFilename": "doc1.docx",
                    "downloadUrl": "/api/v1/tools/executions/uuid1/download/",
                    ...
                },
                ...
            ]
        }
        """
        execution_ids = request.data.get("executionIds", [])

        if not execution_ids:
            return Response(
                {"error": "executionIds is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Filter by user to ensure users can only check their own executions
        executions = ToolExecution.objects.filter(id__in=execution_ids, user=request.user)

        results = []
        for execution in executions:
            result = {
                "executionId": str(execution.id),
                "status": execution.status,
                "filename": execution.input_filename,
                "outputFilename": execution.output_filename,
                "createdAt": execution.created_at.isoformat() if execution.created_at else None,
                "completedAt": execution.completed_at.isoformat()
                if execution.completed_at
                else None,
                "error": execution.error_message if execution.status == "failed" else None,
            }

            if execution.status == "completed":
                result["downloadUrl"] = f"/api/v1/executions/{execution.id}/download/"

            results.append(result)

        return Response({"executions": results})

    @action(detail=True, methods=["get"], url_path="status")
    def check_status(self, request, pk=None):
        """
        Check status of async conversion job.

        GET /api/v1/tools/executions/{execution_id}/status/

        Returns:
        {
            "executionId": "uuid",
            "status": "pending|processing|completed|failed",
            "createdAt": "2025-12-01T10:00:00Z",
            "startedAt": "2025-12-01T10:00:05Z",
            "completedAt": "2025-12-01T10:00:30Z",
            "durationSeconds": 25.0,
            "inputFilename": "document.pdf",
            "outputFilename": "document.docx",
            "outputSize": 524288,
            "downloadUrl": "/api/v1/tools/executions/{id}/download/",
            "error": null
        }
        """
        try:
            # Ensure users can only check status of their own executions
            execution = ToolExecution.objects.get(id=pk, user=request.user)

            response_data = {
                "executionId": str(execution.id),
                "status": execution.status,
                "createdAt": execution.created_at.isoformat() if execution.created_at else None,
                "startedAt": execution.started_at.isoformat() if execution.started_at else None,
                "completedAt": execution.completed_at.isoformat()
                if execution.completed_at
                else None,
                "durationSeconds": execution.duration_seconds,
                "inputFilename": execution.input_filename,
                "outputFilename": execution.output_filename,
                "outputSize": execution.output_size,
                "error": execution.error_message if execution.status == "failed" else None,
            }

            # Add download URL if completed
            if execution.status == "completed":
                response_data["downloadUrl"] = f"/api/v1/executions/{pk}/download/"

            return Response(response_data)

        except ToolExecution.DoesNotExist:
            return Response(
                {"error": "Execution not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["get"], url_path="download")
    def download_result(self, request, pk=None):
        """
        Download the converted file from Azure Blob Storage.

        GET /api/v1/tools/executions/{execution_id}/download/
        """
        from django.conf import settings
        from django.http import HttpResponse

        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        try:
            # Ensure users can only download their own files
            execution = ToolExecution.objects.get(id=pk, user=request.user)

            if execution.status != "completed":
                return Response(
                    {"error": f"Execution not completed. Current status: {execution.status}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Determine container and blob name from output_blob_path
            container_name = "processed"  # Default container
            blob_name = None
            
            if execution.output_blob_path:
                # Parse the output_blob_path which includes container/blob format
                # Examples:
                #   - processed/docx/{uuid}.docx
                #   - processed/image/{uuid}.png
                #   - processed/gpx/{uuid}.gpx
                #   - video-processed/video/{uuid}.mp4
                path_parts = execution.output_blob_path.split("/", 1)
                if len(path_parts) == 2:
                    container_name = path_parts[0]
                    blob_name = path_parts[1]
                else:
                    blob_name = execution.output_blob_path
                    
                logger.info(f"Parsed output_blob_path: container={container_name}, blob={blob_name}")
            elif execution.output_file and execution.output_file.name:
                # Fallback to output_file field
                blob_name = execution.output_file.name
                # Remove container prefix if present
                if blob_name.startswith("processed/"):
                    blob_name = blob_name[len("processed/"):]
                elif blob_name.startswith("video-processed/"):
                    container_name = "video-processed"
                    blob_name = blob_name[len("video-processed/"):]
            else:
                # Last resort: guess based on tool name
                if execution.tool_name == "video-rotation":
                    container_name = "video-processed"
                    blob_name = f"video/{execution.id}.mp4"
                elif execution.tool_name == "pdf-docx-converter":
                    blob_name = f"docx/{execution.id}.docx"
                elif execution.tool_name == "image-format-converter":
                    blob_name = f"image/{execution.id}.png"  # Default extension
                elif execution.tool_name in ["gpx-kml-converter", "gpx-speed-modifier"]:
                    blob_name = f"gpx/{execution.id}.gpx"
                else:
                    return Response(
                        {"error": "Cannot determine output file location"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            
            logger.info(f"Download request - Tool: {execution.tool_name}")
            logger.info(f"Using container: {container_name}, blob: {blob_name}")
            logger.info(f"About to initialize blob service client...")

            # Initialize blob service client using the helper function
            blob_service = get_blob_service_client()

            # Download blob
            logger.info(f"Downloading blob: {blob_name} from container: {container_name}")
            blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)

            # Check if blob exists
            logger.info(f"Checking if blob exists...")
            blob_exists = blob_client.exists()
            logger.info(f"Blob exists: {blob_exists}")
            
            if not blob_exists:
                logger.error(f"Blob not found: {blob_name}")
                # Try alternative blob name without path
                if execution.tool_name == "video-rotation":
                    alt_blob_name = f"{execution.id}.mp4"
                else:
                    alt_blob_name = f"{execution.id}.docx"
                logger.info(f"Trying alternative blob name: {alt_blob_name}")
                blob_client = blob_service.get_blob_client(
                    container=container_name, blob=alt_blob_name
                )
                if not blob_client.exists():
                    return Response(
                        {"error": "Converted file not found in storage"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            logger.info(f"Starting blob download...")
            blob_data = blob_client.download_blob().readall()

            logger.info(f"✅ Downloaded {len(blob_data)} bytes for execution {execution.id}")

            # Determine output filename and content type
            output_filename = execution.output_filename or "download"
            
            # Add default extension if no filename available
            if not output_filename or output_filename == "download":
                if execution.tool_name == "video-rotation":
                    output_filename = "rotated_video.mp4"
                elif execution.tool_name == "pdf-docx-converter":
                    output_filename = "converted.docx"
                elif execution.tool_name == "image-format-converter":
                    output_filename = "converted.png"
                elif execution.tool_name in ["gpx-kml-converter", "gpx-speed-modifier"]:
                    output_filename = "track.gpx"
                else:
                    output_filename = "download.bin"
            
            file_ext = output_filename.split(".")[-1].lower()
            content_type_map = {
                # Documents
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "pdf": "application/pdf",
                "txt": "text/plain",
                # Videos
                "mp4": "video/mp4",
                "avi": "video/x-msvideo",
                "mov": "video/quicktime",
                "mkv": "video/x-matroska",
                "webm": "video/webm",
                "flv": "video/x-flv",
                "wmv": "video/x-ms-wmv",
                "m4v": "video/x-m4v",
                "mpg": "video/mpeg",
                "mpeg": "video/mpeg",
                "3gp": "video/3gpp",
                # Images
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "gif": "image/gif",
                "webp": "image/webp",
                "bmp": "image/bmp",
                "tiff": "image/tiff",
                "tif": "image/tiff",
                "ico": "image/x-icon",
                "svg": "image/svg+xml",
                # GPS/Map formats
                "gpx": "application/gpx+xml",
                "kml": "application/vnd.google-earth.kml+xml",
                "kmz": "application/vnd.google-earth.kmz",
            }
            content_type = content_type_map.get(file_ext, "application/octet-stream")

            # Return file
            response = HttpResponse(blob_data, content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{output_filename}"'
            response["Content-Length"] = str(len(blob_data))
            return response

        except ToolExecution.DoesNotExist:
            return Response(
                {"error": "Execution not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Failed to download result: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to download file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_result(self, request, pk=None):
        """
        Delete the execution record and its associated blob from storage.

        DELETE /api/v1/executions/{execution_id}/delete/
        """
        from django.conf import settings

        try:
            # Ensure users can only delete their own files
            execution = ToolExecution.objects.get(id=pk, user=request.user)

            if execution.status not in ["completed", "failed"]:
                return Response(
                    {"error": f"Cannot delete execution with status: {execution.status}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Determine container and blob name for deletion
            if execution.tool_name == "video-rotation":
                container_name = "video-processed"
                if execution.output_blob_path:
                    blob_name = execution.output_blob_path
                    if blob_name.startswith("video-processed/"):
                        blob_name = blob_name[len("video-processed/"):]
                else:
                    blob_name = f"video/{execution.id}.mp4"
            else:
                # PDF and other tools
                container_name = "processed"
                if execution.output_file and execution.output_file.name:
                    blob_name = execution.output_file.name
                    if blob_name.startswith("processed/"):
                        blob_name = blob_name[len("processed/"):]
                else:
                    blob_name = f"docx/{execution.id}.docx"

            # Delete blob from storage if it exists
            try:
                blob_service = get_blob_service_client()
                blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
                
                if blob_client.exists():
                    blob_client.delete_blob()
                    logger.info(f"Deleted blob: {container_name}/{blob_name}")
                else:
                    logger.warning(f"Blob not found for deletion: {container_name}/{blob_name}")
            except Exception as blob_error:
                logger.error(f"Failed to delete blob: {blob_error}")
                # Continue with database deletion even if blob deletion fails

            # Delete the execution record from database
            execution.delete()
            logger.info(f"Deleted execution record: {pk}")

            return Response(
                {"message": "Execution and file deleted successfully"},
                status=status.HTTP_200_OK,
            )

        except ToolExecution.DoesNotExist:
            return Response(
                {"error": "Execution not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Failed to delete result: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to delete file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

