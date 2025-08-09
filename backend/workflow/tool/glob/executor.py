import os
import glob
from typing import List
from pathlib import Path

from common.type.agent import AgentExecuteType, AgentExecuteResult, GlobToolResult
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from workflow.tool.glob.tool import GlobToolParam, GlobTool
from workflow.service.schema import BashOps

@register_tool("glob_tool")
class GlobToolExecutor(BaseTool):
    param_class = GlobToolParam
    tool_definition = GlobTool
    execute_type = AgentExecuteType.TOOL_GLOB  # Using TOOL_GLOB type

    async def _executor(self,
        sandbox: DaytonaSandbox, job_dir: str, param: GlobToolParam
    ) -> str:
        if param.path:
            search_dir = os.path.join(job_dir, param.path)
        else:
            search_dir = job_dir
        bash_ops = BashOps(cmd=f'glob {param.pattern} {search_dir}')
        
        try:
            result = await sandbox.run_bash(bash_ops=bash_ops, cwd=search_dir)
            return result
        except Exception as e:
            logger.error(f"Executing bash command with exception: {e}")
            return f'Running glob command failed with exception: {e}'
            
    
    async def execute(self, params: GlobToolParam, context):
        await self.send_init_message(
            context,
            execute_result=AgentExecuteResult(
                tool_bash_result=None  # Not sending bash result for init
            )
        )

        if context.daytona is None:
            raise ValueError("Daytona sandbox is not available")
        
        # Execute the tool
        result = await self._executor(context.daytona, context.job_dir, params)
        
        # Send complete message with the result
        await self.send_complete_message(
            context,
            execute_result=AgentExecuteResult(
                tool_glob_result=GlobToolResult(
                    pattern=params.pattern,
                    path=params.path,
                    result=result
                )
            )
        )
        
        return result
