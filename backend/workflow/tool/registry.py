from typing import Dict, Type
from workflow.tool.base import BaseTool

class ToolRegistry:
    """Registry for all available tools"""
    _tools: Dict[str, Type[BaseTool]] = {}
    
    @classmethod
    def register(cls, tool_class: Type[BaseTool]):
        """Register a tool class"""
        cls._tools[tool_class.name] = tool_class
        return tool_class
    
    @classmethod
    def get(cls, name: str) -> Type[BaseTool]:
        """Get a tool class by name"""
        if name not in cls._tools:
            raise ValueError(f"Tool {name} not found")
        return cls._tools[name]
    
    @classmethod
    def all(cls) -> Dict[str, Type[BaseTool]]:
        """Get all registered tools"""
        return cls._tools.copy()

# Decorator for registering tools
def register_tool(name: str):
    def decorator(cls):
        cls.name = name
        return ToolRegistry.register(cls)
    return decorator
