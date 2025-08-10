"""workflow.tool package

This package registers tools that are available for the agent to use.
"""

# Import tools - but don't register them yet as they're not class-based tools
from workflow.tool.jira.tool import JiraTool
from workflow.tool.google_docs.tool import GoogleDocsTool
from workflow.tool.registry import ToolRegistry

# Note: JiraTool and GoogleDocsTool are ChatCompletionToolParam dictionaries,
# not tool classes, so they don't need to be registered in the ToolRegistry
# which is for class-based tools

__all__ = ["ToolRegistry", "JiraTool", "GoogleDocsTool"]