"""
Tool registry for plugin discovery and management.

Provides centralized tool registration and lookup.
"""

import logging
from typing import Dict, List, Optional, Type

from .base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for discovering and managing tool plugins.

    Tools are automatically discovered and registered during app startup.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, Type[BaseTool]] = {}

    def register(self, tool_class: Type[BaseTool]) -> None:
        """
        Register a tool plugin.

        Args:
            tool_class: Tool class inheriting from BaseTool

        Raises:
            ValueError: If tool name conflicts with existing tool
        """
        tool_name = tool_class.name

        if not tool_name:
            raise ValueError(f"Tool class {tool_class.__name__} must define a 'name' attribute")

        if tool_name in self._tools:
            logger.warning(f"Tool '{tool_name}' already registered, overwriting")

        self._tools[tool_name] = tool_class
        logger.info(f"Registered tool: {tool_name}")

    def get_tool(self, name: str) -> Optional[Type[BaseTool]]:
        """
        Get tool class by name.

        Args:
            name: Tool name to lookup

        Returns:
            Tool class or None if not found
        """
        return self._tools.get(name)

    def get_tool_instance(self, name: str) -> Optional[BaseTool]:
        """
        Get instantiated tool by name.

        Args:
            name: Tool name to lookup

        Returns:
            Tool instance or None if not found
        """
        tool_class = self.get_tool(name)
        if tool_class:
            return tool_class()
        return None

    def list_tools(self) -> List[Dict]:
        """
        List all registered tools with metadata.

        Returns:
            List of tool metadata dictionaries
        """
        tools = []
        for tool_class in self._tools.values():
            tool_instance = tool_class()
            tools.append(tool_instance.get_metadata())
        return tools

    def is_registered(self, name: str) -> bool:
        """
        Check if tool is registered.

        Args:
            name: Tool name to check

        Returns:
            True if tool is registered
        """
        return name in self._tools

    def discover_tools(self) -> None:
        """
        Discover and register tool plugins.

        Scans the tools.plugins package for tool classes.
        """
        try:
            import importlib
            import inspect
            import pkgutil

            from . import plugins

            # Iterate through all modules in plugins package
            for importer, modname, ispkg in pkgutil.iter_modules(
                plugins.__path__, plugins.__name__ + "."
            ):
                try:
                    # Use importlib instead of deprecated find_module
                    module = importlib.import_module(modname)

                    # Find all BaseTool subclasses in module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, BaseTool)
                            and obj is not BaseTool
                            and obj.__module__ == module.__name__
                        ):
                            self.register(obj)

                except Exception as e:
                    logger.error(f"Failed to load tool module '{modname}': {e}")

        except ImportError:
            logger.warning("No plugins package found, no tools registered")


# Global registry instance
tool_registry = ToolRegistry()
