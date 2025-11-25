"""
Serializers for tool API endpoints.
"""
from rest_framework import serializers
from .models import ToolExecution


class ToolMetadataSerializer(serializers.Serializer):
    """Serializer for tool metadata."""
    
    name = serializers.CharField()
    display_name = serializers.CharField(source='displayName')
    description = serializers.CharField()
    category = serializers.CharField()
    version = serializers.CharField()
    allowed_input_types = serializers.ListField(
        child=serializers.CharField(),
        source='allowedInputTypes'
    )
    max_file_size = serializers.IntegerField(source='maxFileSize')


class ToolProcessRequestSerializer(serializers.Serializer):
    """Serializer for tool processing request."""
    
    tool_name = serializers.CharField(source='toolName')
    file = serializers.FileField()
    parameters = serializers.JSONField(default=dict, required=False)
    
    def validate_tool_name(self, value):
        """Validate that tool exists."""
        from .registry import tool_registry
        
        if not tool_registry.is_registered(value):
            raise serializers.ValidationError(f"Tool '{value}' not found")
        return value


class ToolProcessResponseSerializer(serializers.Serializer):
    """Serializer for tool processing response."""
    
    execution_id = serializers.UUIDField(source='executionId')
    status = serializers.CharField()
    message = serializers.CharField()


class ToolExecutionSerializer(serializers.ModelSerializer):
    """Serializer for tool execution records."""
    
    class Meta:
        model = ToolExecution
        fields = [
            'id', 'tool_name', 'status', 'input_filename', 'output_filename',
            'output_file', 'parameters', 'started_at', 'completed_at',
            'duration_seconds', 'error_message', 'input_size', 'output_size',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class ToolExecutionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for tool execution list."""
    
    class Meta:
        model = ToolExecution
        fields = [
            'id', 'tool_name', 'status', 'input_filename', 'output_filename',
            'duration_seconds', 'input_size', 'output_size', 'created_at'
        ]
        read_only_fields = fields
