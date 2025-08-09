from abc import ABC, abstractmethod
from typing import Type, Optional, Any, Dict, Callable
from pydantic import BaseModel
from litellm import ChatCompletionToolParam
from common.type.agent import AgentExecuteData, AgentExecuteType, CurrentState
import pydantic
from workflow.tool.context import ToolContext

# Rebuild agent models to resolve forward references
from common.type.agent import rebuild_models
rebuild_models()

class BaseTool(ABC):
    """Base class for all tools with common execution patterns"""
    
    # Tool metadata
    name: str
    param_class: Type[BaseModel]
    tool_definition: ChatCompletionToolParam
    execute_type: AgentExecuteType
    
    def __init__(self):
        self.validators: Dict[str, Callable] = {}
        self.pre_hooks: list[Callable] = []
        self.post_hooks: list[Callable] = []
    
    @abstractmethod
    async def execute(self, params: BaseModel, context: ToolContext) -> Any:
        """Execute the tool logic"""
        pass
    
    async def validate_params(self, args: str, agent) -> BaseModel:
        """Validate and parse parameters with fallback"""
        try:
            return self.param_class.model_validate_json(args)
        except pydantic.ValidationError:
            fixed_params = await agent.fix_tool_call_params(args, self.param_class)
            return self.param_class.model_validate_json(fixed_params)
    
    async def send_init_message(self, context: 'ToolContext', **kwargs):
        """Send initialization message"""
        await context.on_client_message(
            data=AgentExecuteData(
                uuid=context.tool_call_uuid,
                current_state=CurrentState.INIT,
                error_flag=False,
                execute_type=self.execute_type,
                execute_result=kwargs.get('execute_params')
            )
        )
    
    async def send_complete_message(self, context: ToolContext, **kwargs):
        """Send completion message"""
        await context.on_client_message(
            data=AgentExecuteData(
                uuid=context.tool_call_uuid,
                current_state=CurrentState.COMPLETE,
                error_flag=False,
                execute_type=self.execute_type,
                execute_result=kwargs.get('execute_result')
            )
        )
