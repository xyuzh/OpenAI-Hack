import os
from workflow.tool.file_read.tool import FileReadParam, FileReadTool
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from common.type.agent import AgentExecuteType, AgentExecuteResult, FileReadResult
from workflow.service.schema import BashOps


@register_tool("file_read")
class FileReadToolExecutor(BaseTool):
    param_class = FileReadParam
    tool_definition = FileReadTool
    execute_type = AgentExecuteType.TOOL_FILE_READ

    async def _executor(
        self, file_read_param: FileReadParam, daytona: DaytonaSandbox, job_dir: str
    ) -> str:
        try:
            file_path = os.path.join(job_dir, file_read_param.file_path)
            offset = file_read_param.offset or 1
            limit = max(1, file_read_param.limit or 2000)
            end_line = offset + limit - 1
            sed_cmd = f'sed -n "{offset},{end_line}p" "{file_path}"'

            return await daytona.run_bash(BashOps(cmd=sed_cmd), cwd=job_dir)
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return f'File read failed: {e}'

    async def execute(self, params: FileReadParam, context):
        # Send init message
        await self.send_init_message(
            context,
            execute_result=AgentExecuteResult(
                tool_file_read_result=FileReadResult(
                    file_path=params.file_path,
                )
            ),
        )

        if context.daytona is None:
            raise ValueError("Daytona sandbox is not available")

        # Execute the tool
        result = await self._executor(params, context.daytona, context.job_dir)

        # Send complete message
        await self.send_complete_message(
            context,
            execute_result=AgentExecuteResult(
                tool_file_read_result=FileReadResult(
                    file_path=params.file_path,
                    content=result,
                )
            ),
        )

        return result
