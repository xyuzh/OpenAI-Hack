from workflow.tool.todo_write.tool import TodoWriteParam, TodoWriteTool
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from common.type.agent import AgentExecuteType, AgentExecuteResult


@register_tool("todo_write")
class TodoWriteToolExecutor(BaseTool):
    param_class = TodoWriteParam
    tool_definition = TodoWriteTool
    execute_type = AgentExecuteType.TOOL_TODO_WRITE

    async def _executor(self, params: TodoWriteParam, job_state, job_state_repo, job_id: str):
        try:
            # Validate that only one task is in_progress
            in_progress_count = sum(1 for todo in params.todos if todo.status == 'in_progress')
            if in_progress_count > 1:
                return "Error: Only one task can be in_progress at a time."
            
            # Update the job state with new todo list
            job_state.todo_list = params.todos
            
            return (f"Todo list updated.")
            
        except Exception as e:
            logger.error(f"Error writing todos: {e}")
            return f"Error writing todos: {e}"
    
    async def execute(self, params: TodoWriteParam, context):
        # Send init message
        await self.send_init_message(context)
        
        if context.job_state is None:
            raise ValueError("Job state is not available")
        
        if context.runner.job_state_repo is None:
            raise ValueError("Job state repository is not available")
            
        # Execute the tool
        result = await self._executor(
            params, 
            context.job_state, 
            context.runner.job_state_repo,
            context.job_state.id
        )
        
        # Send complete message
        await self.send_complete_message(
            context,
            execute_result=AgentExecuteResult(
                tool_todo_write_result=params,
            )
        )
        
        return result 