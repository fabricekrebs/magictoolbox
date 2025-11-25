"""
Views for tool operations (both web UI and API endpoints).
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django import forms
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ToolExecution
from .serializers import (
    ToolMetadataSerializer,
    ToolProcessRequestSerializer,
    ToolProcessResponseSerializer,
    ToolExecutionSerializer,
    ToolExecutionListSerializer
)
from .registry import tool_registry
from .tasks import process_tool_async
import logging

logger = logging.getLogger(__name__)


# Template Views
def tool_list(request):
    """
    Display list of available tools.
    """
    tools = tool_registry.list_tools()
    return render(request, 'tools/tool_list.html', {'tools': tools})


def tool_detail(request, tool_slug):
    """
    Display tool detail and processing interface.
    """
    tool_instance = tool_registry.get_tool_instance(tool_slug)
    if not tool_instance:
        return render(request, 'errors/404.html', status=404)
    
    metadata = tool_instance.get_metadata()
    
    # Create a dynamic form based on tool requirements
    class ToolForm(forms.Form):
        file = forms.FileField(
            label='Upload File',
            help_text=f"Maximum file size: {metadata.get('max_file_size', '50MB')}"
        )
    
    form = ToolForm()
    
    context = {
        'tool': metadata,
        'form': form,
    }
    
    # Use tool-specific template if it exists
    template_name = f'tools/{tool_slug.replace("-", "_")}.html'
    try:
        return render(request, template_name, context)
    except Exception as e:
        # Fall back to generic template
        logger.warning(f"Error rendering {template_name}: {e}")
        return render(request, 'tools/tool_detail.html', context)


class ToolViewSet(viewsets.ViewSet):
    """
    ViewSet for tool operations.
    
    Provides endpoints for:
    - Listing available tools
    - Processing files with tools
    """
    permission_classes = []  # Allow public access for testing
    
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
                {'error': {'message': f"Tool '{pk}' not found", 'code': 'tool_not_found'}},
                status=status.HTTP_404_NOT_FOUND
            )
        
        metadata = tool_instance.get_metadata()
        serializer = ToolMetadataSerializer(metadata)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='convert')
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
        from django.http import HttpResponse
        import zipfile
        import io
        
        tool_instance = tool_registry.get_tool_instance(pk)
        if not tool_instance:
            return Response(
                {'error': 'Tool not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Handle both single file and multiple files
        files = request.FILES.getlist('files[]') or request.FILES.getlist('files')
        if not files:
            # Try single file upload
            single_file = request.FILES.get('file')
            if single_file:
                files = [single_file]
        
        if not files:
            return Response(
                {'error': 'No files provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get parameters from request - handle different tool types
        parameters = {}
        
        # Image converter parameters
        if request.data.get('output_format'):
            parameters['output_format'] = request.data.get('output_format')
        if request.data.get('quality'):
            parameters['quality'] = request.data.get('quality')
        if request.data.get('width'):
            parameters['width'] = request.data.get('width')
        if request.data.get('height'):
            parameters['height'] = request.data.get('height')
        
        # GPX/KML converter parameters
        if request.data.get('conversion_type'):
            parameters['conversion_type'] = request.data.get('conversion_type')
        if request.data.get('name'):
            parameters['name'] = request.data.get('name')
        
        # GPX Speed Modifier parameters
        if request.data.get('mode'):
            parameters['mode'] = request.data.get('mode')
        if request.data.get('speed_multiplier'):
            parameters['speed_multiplier'] = request.data.get('speed_multiplier')
        
        # Process multiple files
        if len(files) > 1:
            # Create a ZIP file with all converted images
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
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
                        with open(output_path, 'rb') as f:
                            zip_file.writestr(output_filename, f.read())
                        
                        # Cleanup
                        tool_instance.cleanup(output_path)
                        
                    except Exception as e:
                        logger.error(f"Failed to convert {file.name}: {e}")
                        continue
            
            # Return ZIP file
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="converted_images.zip"'
            return response
        
        else:
            # Single file conversion
            file = files[0]
            
            # Validate
            is_valid, error_msg = tool_instance.validate(file, parameters)
            if not is_valid:
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Process synchronously for immediate response
                output_path, output_filename = tool_instance.process(file, parameters)
                
                # Special handling for JSON responses (e.g., GPX analyze mode)
                file_ext = output_filename.split('.')[-1].lower()
                if file_ext == 'json':
                    # Read JSON and return as JSON response
                    import json
                    with open(output_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    
                    # Cleanup
                    tool_instance.cleanup(output_path)
                    
                    # Return JSON response
                    return Response(json_data)
                
                # Read the output file
                with open(output_path, 'rb') as f:
                    output_data = f.read()
                
                # Cleanup
                tool_instance.cleanup(output_path)
                
                # Determine content type based on file extension
                content_type_map = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'webp': 'image/webp',
                    'gif': 'image/gif',
                    'bmp': 'image/bmp',
                    'tiff': 'image/tiff',
                    'tif': 'image/tiff',
                    'ico': 'image/x-icon',
                    'svg': 'image/svg+xml',
                    'gpx': 'application/gpx+xml',
                    'kml': 'application/vnd.google-earth.kml+xml',
                    'xml': 'application/xml',
                }
                content_type = content_type_map.get(file_ext, 'application/octet-stream')
                
                # Return the converted file
                response = HttpResponse(output_data, content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{output_filename}"'
                return response
                
            except Exception as e:
                logger.error(f"Image conversion failed: {e}")
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    @action(detail=False, methods=['post'])
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
        
        tool_name = serializer.validated_data['toolName']
        file = serializer.validated_data['file']
        parameters = serializer.validated_data.get('parameters', {})
        
        # Create execution record
        execution = ToolExecution.objects.create(
            user=request.user,
            tool_name=tool_name,
            input_filename=file.name,
            input_size=file.size,
            parameters=parameters,
            status='pending'
        )
        
        # Save input file
        execution.input_file = file
        execution.save()
        
        # Queue async processing
        process_tool_async.delay(
            execution_id=str(execution.id),
            tool_name=tool_name,
            input_file_path=execution.input_file.path,
            parameters=parameters
        )
        
        response_data = {
            'executionId': str(execution.id),
            'status': 'pending',
            'message': 'Tool processing queued'
        }
        
        response_serializer = ToolProcessResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)


class ToolExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for tool execution history.
    
    Provides read-only access to execution records.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ToolExecutionSerializer
    
    def get_queryset(self):
        """Return executions for current user."""
        return ToolExecution.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Use simplified serializer for list view."""
        if self.action == 'list':
            return ToolExecutionListSerializer
        return ToolExecutionSerializer
