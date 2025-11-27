"""
Celery tasks for async tool processing.
"""

from celery import shared_task
from django.core.files import File
from django.utils import timezone
from .models import ToolExecution
from .registry import tool_registry
from apps.core.exceptions import ToolExecutionError
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_tool_async(
    self, execution_id: str, tool_name: str, input_file_path: str, parameters: dict
):
    """
    Process file with specified tool asynchronously.

    Args:
        execution_id: UUID of ToolExecution record
        tool_name: Name of tool to use
        input_file_path: Path to input file
        parameters: Tool-specific parameters
    """
    execution = None
    temp_files = []

    try:
        # Get execution record
        execution = ToolExecution.objects.get(id=execution_id)
        execution.status = "processing"
        execution.started_at = timezone.now()
        execution.save()

        logger.info(f"Starting tool execution {execution_id} with tool {tool_name}")

        # Get tool instance
        tool = tool_registry.get_tool_instance(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool '{tool_name}' not found")

        # Open input file
        with open(input_file_path, "rb") as f:
            from django.core.files.uploadedfile import InMemoryUploadedFile
            import io

            file_content = f.read()
            uploaded_file = InMemoryUploadedFile(
                file=io.BytesIO(file_content),
                field_name="file",
                name=Path(input_file_path).name,
                content_type="application/octet-stream",
                size=len(file_content),
                charset=None,
            )

            # Validate input
            is_valid, error_message = tool.validate(uploaded_file, parameters)
            if not is_valid:
                raise ToolExecutionError(error_message or "Validation failed")

            # Process file
            output_file_path, output_filename = tool.process(uploaded_file, parameters)
            temp_files.append(output_file_path)

            # Save output file
            with open(output_file_path, "rb") as output_f:
                execution.output_file.save(output_filename, File(output_f), save=False)
                execution.output_filename = output_filename
                execution.output_size = Path(output_file_path).stat().st_size

            # Update execution record
            execution.status = "completed"
            execution.completed_at = timezone.now()

            if execution.started_at:
                duration = (execution.completed_at - execution.started_at).total_seconds()
                execution.duration_seconds = duration

            execution.save()

            logger.info(f"Tool execution {execution_id} completed successfully")

    except Exception as exc:
        logger.error(f"Tool execution {execution_id} failed: {exc}", exc_info=True)

        if execution:
            execution.status = "failed"
            execution.error_message = str(exc)

            import traceback

            execution.error_traceback = traceback.format_exc()

            execution.completed_at = timezone.now()
            if execution.started_at:
                duration = (execution.completed_at - execution.started_at).total_seconds()
                execution.duration_seconds = duration

            execution.save()

        # Retry on failure
        raise self.retry(exc=exc, countdown=60)

    finally:
        # Cleanup temporary files
        if tool_registry.is_registered(tool_name):
            tool = tool_registry.get_tool_instance(tool_name)
            if tool:
                tool.cleanup(*temp_files)
