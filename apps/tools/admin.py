"""Admin configuration for Tools app."""

from django.contrib import admin
from .models import ToolExecution


@admin.register(ToolExecution)
class ToolExecutionAdmin(admin.ModelAdmin):
    """Admin interface for ToolExecution model."""

    list_display = [
        "id",
        "tool_name",
        "user",
        "status",
        "input_filename",
        "output_filename",
        "duration_seconds",
        "created_at",
    ]
    list_filter = ["status", "tool_name", "created_at"]
    search_fields = ["user__email", "user__username", "tool_name", "input_filename"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "duration_seconds",
        "input_size",
        "output_size",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        ("Basic Info", {"fields": ("id", "user", "tool_name", "status")}),
        (
            "Files",
            {
                "fields": (
                    "input_file",
                    "input_filename",
                    "input_size",
                    "output_file",
                    "output_filename",
                    "output_size",
                )
            },
        ),
        ("Parameters", {"fields": ("parameters",)}),
        ("Timing", {"fields": ("created_at", "started_at", "completed_at", "duration_seconds")}),
        ("Errors", {"fields": ("error_message", "error_traceback"), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        """Disable manual creation of executions."""
        return False
