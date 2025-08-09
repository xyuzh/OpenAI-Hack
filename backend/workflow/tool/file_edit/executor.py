import os
from workflow.service.daytona_sandbox import DaytonaSandbox
from typing import List
from workflow.tool.file_edit.tool import FileEditParam, FileEditTool
from daytona_api_client_async.models.replace_result import ReplaceResult
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from common.type.agent import AgentExecuteType, AgentExecuteResult


@register_tool("file_edit")
class FileEditToolExecutor(BaseTool):
    param_class = FileEditParam
    tool_definition = FileEditTool
    execute_type = AgentExecuteType.TOOL_FILES_EDIT

    async def _executor(self, file_edit_param: FileEditParam, daytona: DaytonaSandbox, job_dir: str):
        try:
            file_path = os.path.join(job_dir, file_edit_param.path)
            result = await daytona.file_edit(
                    path=file_path,
                    pattern=file_edit_param.old_str,
                    new_value=file_edit_param.new_str
                )
            if result.success:
                return f"file edited"
            else:
                return f"file {file_edit_param.path} editing failed, {result.error}"
            
        except Exception as e:
            logger.error(f"Error editing files: {e}")
            return f"Error editing files: {e}"
    
    async def execute(self, params: FileEditParam, context):
        # Send init message
        await self.send_init_message(context)
        
        if context.daytona is None:
            raise ValueError("Daytona sandbox is not available")
        
        # Execute the tool
        result = await self._executor(params, context.daytona, context.job_dir)
        
        # Send complete message
        await self.send_complete_message(
            context,
            execute_result=AgentExecuteResult(
                tool_file_edit_result=params,
            )
        )
        
        return result