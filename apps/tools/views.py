"""
Views for tool operations (both web UI and API endpoints).
"""

import logging

from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
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
    Requires authentication.
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
                    storage_account_name = getattr(settings, "AZURE_ACCOUNT_NAME", None)
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
            storage_account_name = getattr(settings, "AZURE_ACCOUNT_NAME", None)
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

        # Special handling for PDF to DOCX converter (Azure Functions only)
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
                    execution_id, _ = tool_instance.process(file, parameters)

                    # Create ToolExecution record
                    _execution = ToolExecution.objects.create(
                        id=execution_id,
                        user=request.user,
                        tool_name=pk,
                        input_filename=file.name,
                        input_size=file.size,
                        parameters=parameters,
                        status="pending",
                    )

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

                    # Create ToolExecution record for tracking
                    _execution = ToolExecution.objects.create(
                        id=execution_id,
                        user=request.user,
                        tool_name=pk,
                        input_filename=file.name,
                        input_size=file.size,
                        parameters=parameters,
                        status="pending",
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
                }
                content_type = content_type_map.get(file_ext, "application/octet-stream")

                # Return the converted file
                response = HttpResponse(output_data, content_type=content_type)
                response["Content-Disposition"] = f'attachment; filename="{output_filename}"'
                return response

            except Exception as e:
                logger.error(f"Image conversion failed: {e}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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


class ToolExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for tool execution history.

    Provides read-only access to execution records.
    """

    permission_classes = [IsAuthenticated]  # Require authentication
    serializer_class = ToolExecutionSerializer

    def get_queryset(self):
        """Return executions for the authenticated user only."""
        return ToolExecution.objects.filter(user=self.request.user)

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

            # Get blob name from execution record or construct from execution_id
            # The output_file field contains the full path including container (e.g., "processed/docx/{uuid}.docx")
            # We need to strip the container name since we specify it separately
            if execution.output_file and execution.output_file.name:
                blob_name = execution.output_file.name
                # Remove "processed/" prefix if present
                if blob_name.startswith("processed/"):
                    blob_name = blob_name[len("processed/"):]
            else:
                blob_name = f"docx/{execution.id}.docx"
            logger.info(f"Using blob name: {blob_name}")

            # Initialize blob service client - handle both local and production
            connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None)

            if connection_string and "127.0.0.1" in connection_string:
                # Local development with Azurite
                logger.info("Using local Azurite for blob download")
                blob_service = BlobServiceClient.from_connection_string(connection_string)
            else:
                # Production with Azure Managed Identity
                storage_account_name = getattr(settings, "AZURE_ACCOUNT_NAME", None)
                if not storage_account_name:
                    return Response(
                        {"error": "Storage account not configured"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                logger.info(
                    f"Using Azure Managed Identity for storage account: {storage_account_name}"
                )
                account_url = f"https://{storage_account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                blob_service = BlobServiceClient(account_url=account_url, credential=credential)

            # Download blob
            logger.info(f"Downloading blob: {blob_name} from container: processed")
            blob_client = blob_service.get_blob_client(container="processed", blob=blob_name)

            # Check if blob exists
            if not blob_client.exists():
                logger.error(f"Blob not found: {blob_name}")
                # Try alternative blob name without path
                alt_blob_name = f"{execution.id}.docx"
                logger.info(f"Trying alternative blob name: {alt_blob_name}")
                blob_client = blob_service.get_blob_client(
                    container="processed", blob=alt_blob_name
                )
                if not blob_client.exists():
                    return Response(
                        {"error": "Converted file not found in storage"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            blob_data = blob_client.download_blob().readall()

            logger.info(f"Downloaded {len(blob_data)} bytes for execution {execution.id}")

            # Determine content type
            output_filename = execution.output_filename or "converted.docx"
            file_ext = output_filename.split(".")[-1].lower()
            content_type_map = {
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "pdf": "application/pdf",
                "txt": "text/plain",
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
