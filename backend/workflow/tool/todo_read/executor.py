import json
from workflow.tool.todo_read.tool import TodoReadParam, TodoReadTool
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from common.type.agent import AgentExecuteType, AgentExecuteResult
from workflow.tool.todo_write.tool import TodoWriteParam

@register_tool("todo_read")
class TodoReadToolExecutor(BaseTool):
    param_class = TodoReadParam
    tool_definition = TodoReadTool
    execute_type = AgentExecuteType.TOOL_TODO_READ

    async def _executor(self, params: TodoReadParam, job_state):
        try:
            # Get the todo list from job state
            todo_list = job_state.todo_list
            
            if not todo_list:
                return "The todo list is empty."
   
            return json.dumps([todo.model_dump() for todo in job_state.todo_list])
            
        except Exception as e:
            logger.error(f"Error reading todos: {e}")
            return f"Error reading todos: {e}"
    
    async def execute(self, params: TodoReadParam, context):
        # Send init message
        await self.send_init_message(context)
        
        if context.job_state is None:
            raise ValueError("Job state is not available")
        
        # Execute the tool
        result = await self._executor(params, context.job_state)
        
        # Send complete message
        await self.send_complete_message(
            context,
            execute_result=AgentExecuteResult(
                tool_todo_read_result=TodoWriteParam(todos=context.job_state.todo_list),
            )
        )
        
        return result 