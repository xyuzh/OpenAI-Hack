from typing import Any
from workflow.tool.registry import ToolRegistry
from workflow.tool.context import ToolContext

from common.utils.string_utils import generate_uuid
from common.type.domain import DomainType

class ToolExecutor:
    """Centralized tool executor"""
    
    def __init__(self):
        self.registry = ToolRegistry
    
    async def execute(self, tool_call, runner_context) -> Any:
        """Execute a tool call with the new architecture"""
        # Extract basic info
        func_name = tool_call.function.name
        args = tool_call.function.arguments
        tool_call_uuid = generate_uuid(DomainType.TASK_AGENT_EXECUTE)
        
        # Get the tool class
        tool_class = self.registry.get(func_name)
        tool = tool_class()
        
        # Create context
        context = ToolContext(
            tool_call_uuid=tool_call_uuid,
            runner=runner_context,  # Pass the whole runner reference
        )
        
        # Validate parameters
        params = await tool.validate_params(args, runner_context.agent)
        
        # Execute with pre/post hooks
        for hook in tool.pre_hooks:
            await hook(params, context)
        
        result = await tool.execute(params, context)
        
        for hook in tool.post_hooks:
            await hook(result, context)
        
        return result
