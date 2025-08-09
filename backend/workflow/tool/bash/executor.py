import os
from common.type.agent import AgentExecuteType, AgentExecuteResult, ToolBashResult
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from workflow.tool.bash.tool import BashToolParam, BashTool
from workflow.service.schema import BashOps


@register_tool("bash_tool")
class BashToolExecutor(BaseTool):
    param_class = BashToolParam
    tool_definition = BashTool
    execute_type = AgentExecuteType.TOOL_BASH

    async def _executor(self,
        sandbox: DaytonaSandbox, job_dir: str, param: BashToolParam
    ) -> str:
        cwd = os.path.join(job_dir, param.cwd) if param.cwd else job_dir
        bash_ops = BashOps(
            cmd=param.cmd,
            timeout=param.timeout,
            env=param.env,
        )
        try:
            if param.is_long_running:
                return await sandbox.run_bash_async(cmd=param.cmd, cwd=cwd)
            else:
                if param.timeout is None:
                    param.timeout = 60
                return await sandbox.run_bash(bash_ops=bash_ops, cwd=cwd)
        except Exception as e:
            logger.error(f"Executing bash command with exception: {e}")
            return f'Running bash command failed with exception: {e}'
    
    async def execute(self, params: BashToolParam, context):
        # Send init message with specific bash result
        await self.send_init_message(
            context,
            execute_result=AgentExecuteResult(
                tool_bash_result=ToolBashResult(
                    cmd=params.cmd,
                    cwd=context.job_dir + params.cwd if params.cwd else context.job_dir,
                )
            )
        )

        if context.daytona is None:
            raise ValueError("Daytona sandbox is not available")
        
        # Execute the tool
        result = await self._executor(context.daytona, context.job_dir, params)
        
        # Send complete message
        await self.send_complete_message(
            context,
            execute_result=AgentExecuteResult(
                tool_bash_result=ToolBashResult(
                    cmd=params.cmd,
                    cwd=context.job_dir + params.cwd if params.cwd else context.job_dir,
                    result=result,
                )
            )
        )
        
        return result


    
