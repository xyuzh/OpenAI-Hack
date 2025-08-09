from workflow.tool.suggest_next_steps.tool import SuggestNextStepsParam, SuggestNextStepsTool
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from common.type.agent import AgentExecuteType, AgentExecuteResult
from workflow.schema.job_state import JobRunState

@register_tool("suggest_next_steps")
class SuggestNextStepsToolExecutor(BaseTool):
    param_class = SuggestNextStepsParam
    tool_definition = SuggestNextStepsTool
    execute_type = AgentExecuteType.TOOL_SUGGEST_NEXT_STEPS

    async def _executor(self, param: SuggestNextStepsParam) -> str:
        # The original executor just logged and returned empty string
        logger.info(f"Job finished with next steps: {param.next_steps}")
        return "Next steps suggested successfully"
    
    async def execute(self, params: SuggestNextStepsParam, context):
        # No init message for job finish
        
        if context.daytona is None:
            raise ValueError("Daytona sandbox is not available")
        # Suspend the job
        context.job_state.state = JobRunState.PENDING
        # Execute the tool
        result = await self._executor(params)
        
        # Send complete message with next steps
        await self.send_complete_message(
            context,
            execute_result=AgentExecuteResult(
                tool_suggest_next_steps_result=params.next_steps,
            )
        )
        
        return result
