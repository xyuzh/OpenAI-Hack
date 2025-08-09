import os
from common.type.agent import AgentExecuteType, AgentExecuteResult
from workflow.service.daytona_sandbox import FileItem
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.file_write.tool import FileWriteParam, FilesCreationTool
from workflow.tool.registry import register_tool


@register_tool("file_write")
class FileWriteToolExecutor(BaseTool):
    param_class = FileWriteParam
    tool_definition = FilesCreationTool
    execute_type = AgentExecuteType.TOOL_FILES_CREATION

    async def _executor(
        self, param: FileWriteParam, daytona: DaytonaSandbox, job_dir: str
    ) -> str:
        try:
            files_upload = []
            file_path = os.path.join(job_dir, param.file_path)
            files_upload.append(FileItem(path=file_path, content=param.content))
            await daytona.upload_files(files_upload)
            return 'File created'

        except Exception as e:
            logger.error(f"Error creating files: {e}")
            raise e
    
    async def execute(self, params: FileWriteParam, context):
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
                tool_file_write_result=params,
            )
        )
        
        return result
