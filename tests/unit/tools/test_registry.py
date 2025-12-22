"""
Unit tests for ToolRegistry.

Tests tool registration, retrieval, and discovery mechanisms.
"""

import pytest
from unittest.mock import Mock, patch

from apps.tools.base import BaseTool
from apps.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    name = "mock-tool"
    display_name = "Mock Tool"
    description = "A mock tool for testing"
    category = "test"
    allowed_input_types = [".txt"]
    max_file_size = 1024 * 1024  # 1MB
    
    def validate(self, input_file, parameters):
        return True, None
    
    def process(self, input_file, parameters):
        return "/path/to/output.txt", "output.txt"
    
    def cleanup(self, *file_paths):
        pass


class DuplicateTool(BaseTool):
    """Duplicate tool with same name."""
    
    name = "mock-tool"  # Same as MockTool
    display_name = "Duplicate Tool"
    description = "Duplicate for testing"
    category = "test"
    allowed_input_types = [".txt"]
    max_file_size = 1024 * 1024
    
    def validate(self, input_file, parameters):
        return True, None
    
    def process(self, input_file, parameters):
        return "/path/to/output.txt", "output.txt"
    
    def cleanup(self, *file_paths):
        pass


class TestToolRegistry:
    """Test suite for ToolRegistry class."""
    
    def test_registry_initialization(self):
        """Test that registry initializes with empty tools dict."""
        registry = ToolRegistry()
        assert registry._tools == {}
    
    def test_register_tool(self):
        """Test registering a new tool."""
        registry = ToolRegistry()
        registry.register(MockTool)
        
        assert "mock-tool" in registry._tools
        assert registry._tools["mock-tool"] == MockTool
    
    def test_register_tool_without_name_raises_error(self):
        """Test that registering tool without name raises ValueError."""
        class NoNameTool(BaseTool):
            name = ""  # Empty name
            display_name = "No Name"
            description = "Test"
            category = "test"
            allowed_input_types = []
            max_file_size = 1024
            
            def validate(self, input_file, parameters):
                return True, None
            
            def process(self, input_file, parameters):
                return "", ""
            
            def cleanup(self, *file_paths):
                pass
        
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="must define a 'name' attribute"):
            registry.register(NoNameTool)
    
    def test_register_duplicate_tool_logs_warning(self, caplog):
        """Test that registering duplicate tool logs warning."""
        registry = ToolRegistry()
        registry.register(MockTool)
        registry.register(DuplicateTool)
        
        assert "already registered" in caplog.text
        # Should overwrite with new tool
        assert registry._tools["mock-tool"] == DuplicateTool
    
    def test_get_tool_returns_tool_class(self):
        """Test retrieving tool class by name."""
        registry = ToolRegistry()
        registry.register(MockTool)
        
        tool_class = registry.get_tool("mock-tool")
        assert tool_class == MockTool
    
    def test_get_tool_returns_none_for_missing_tool(self):
        """Test that get_tool returns None for non-existent tool."""
        registry = ToolRegistry()
        tool_class = registry.get_tool("nonexistent-tool")
        assert tool_class is None
    
    def test_get_tool_instance_returns_instance(self):
        """Test retrieving tool instance."""
        registry = ToolRegistry()
        registry.register(MockTool)
        
        tool_instance = registry.get_tool_instance("mock-tool")
        assert isinstance(tool_instance, MockTool)
        assert tool_instance.name == "mock-tool"
    
    def test_get_tool_instance_returns_none_for_missing_tool(self):
        """Test that get_tool_instance returns None for non-existent tool."""
        registry = ToolRegistry()
        tool_instance = registry.get_tool_instance("nonexistent-tool")
        assert tool_instance is None
    
    def test_list_tools_returns_metadata(self):
        """Test listing all tools returns metadata dictionaries."""
        registry = ToolRegistry()
        registry.register(MockTool)
        
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "mock-tool"
        assert tools[0]["displayName"] == "Mock Tool"
        assert tools[0]["category"] == "test"
    
    def test_is_registered_returns_true_for_registered_tool(self):
        """Test is_registered returns True for registered tool."""
        registry = ToolRegistry()
        registry.register(MockTool)
        
        assert registry.is_registered("mock-tool") is True
    
    def test_is_registered_returns_false_for_unregistered_tool(self):
        """Test is_registered returns False for unregistered tool."""
        registry = ToolRegistry()
        assert registry.is_registered("nonexistent-tool") is False
    
    def test_list_tools_with_multiple_tools(self):
        """Test listing multiple registered tools."""
        class AnotherTool(BaseTool):
            name = "another-tool"
            display_name = "Another Tool"
            description = "Another test tool"
            category = "test"
            allowed_input_types = [".pdf"]
            max_file_size = 5 * 1024 * 1024
            
            def validate(self, input_file, parameters):
                return True, None
            
            def process(self, input_file, parameters):
                return "", ""
            
            def cleanup(self, *file_paths):
                pass
        
        registry = ToolRegistry()
        registry.register(MockTool)
        registry.register(AnotherTool)
        
        tools = registry.list_tools()
        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "mock-tool" in tool_names
        assert "another-tool" in tool_names
    
    @patch('apps.tools.registry.importlib.import_module')
    @patch('apps.tools.registry.pkgutil.iter_modules')
    def test_discover_tools_scans_plugins(self, mock_iter, mock_import):
        """Test that discover_tools scans plugin modules."""
        # Mock plugin discovery
        mock_iter.return_value = [
            (None, "apps.tools.plugins.test_tool", False)
        ]
        
        # Mock module with tool class
        mock_module = Mock()
        mock_module.__name__ = "apps.tools.plugins.test_tool"
        mock_module.TestTool = MockTool
        mock_import.return_value = mock_module
        
        registry = ToolRegistry()
        
        with patch('apps.tools.registry.inspect.getmembers') as mock_members:
            mock_members.return_value = [("TestTool", MockTool)]
            registry.discover_tools()
        
        assert registry.is_registered("mock-tool")
    
    def test_discover_tools_handles_import_errors(self, caplog):
        """Test that discover_tools handles module import errors gracefully."""
        registry = ToolRegistry()
        
        with patch('apps.tools.registry.pkgutil.iter_modules') as mock_iter:
            mock_iter.return_value = [
                (None, "apps.tools.plugins.broken_tool", False)
            ]
            
            with patch('apps.tools.registry.importlib.import_module') as mock_import:
                mock_import.side_effect = ImportError("Module not found")
                
                # Should not raise exception
                registry.discover_tools()
                
                assert "Failed to load tool module" in caplog.text
