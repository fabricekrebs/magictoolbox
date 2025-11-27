from django.apps import AppConfig


class ToolsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tools"
    verbose_name = "Tools"

    def ready(self):
        """Register tools when app is ready."""
        from .registry import tool_registry

        tool_registry.discover_tools()
