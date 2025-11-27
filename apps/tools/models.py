"""
Models for tool execution tracking.
"""

from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel, UUIDModel

User = get_user_model()


class ToolExecution(UUIDModel, TimeStampedModel):
    """
    Track tool execution history and results.

    Stores metadata about tool runs including input/output files,
    parameters, status, and error information.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tool_executions")
    tool_name = models.CharField(max_length=100, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    # Input/Output
    input_file = models.FileField(upload_to="tool_inputs/%Y/%m/%d/", null=True, blank=True)
    input_filename = models.CharField(max_length=255)
    output_file = models.FileField(upload_to="tool_outputs/%Y/%m/%d/", null=True, blank=True)
    output_filename = models.CharField(max_length=255, blank=True)

    # Parameters
    parameters = models.JSONField(default=dict, blank=True)

    # Execution metadata
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)

    # File sizes
    input_size = models.BigIntegerField(default=0)
    output_size = models.BigIntegerField(default=0)

    class Meta:
        db_table = "tool_executions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["tool_name", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.tool_name} - {self.status} - {self.user.email}"
