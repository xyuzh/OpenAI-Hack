"""workflow.tool package

This package registers tools that are available for the agent to use.
"""

# Import and register tools
from workflow.tool.jira.tool import JiraTool
from workflow.tool.google_docs.tool import GoogleDocsTool
from workflow.tool.registry import ToolRegistry

# Register tools
ToolRegistry.register(JiraTool)
ToolRegistry.register(GoogleDocsTool)

__all__ = ["ToolRegistry", "JiraTool", "GoogleDocsTool"]