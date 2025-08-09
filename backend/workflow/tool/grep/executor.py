import os

from common.type.agent import AgentExecuteType, AgentExecuteResult, GrepToolResult
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from workflow.tool.grep.tool import GrepToolParam, GrepTool
from workflow.service.schema import BashOps


@register_tool("grep_tool")
class GrepToolExecutor(BaseTool):
    param_class = GrepToolParam
    tool_definition = GrepTool
    execute_type = AgentExecuteType.TOOL_GREP

    async def _executor(self,
        sandbox: DaytonaSandbox, job_dir: str, param: GrepToolParam
    ) -> str:
        # Build the grep command - always recursive with line numbers
        cmd_parts = ['grep', '-r', '-n', '--color=never']
        
        # Add file pattern filter if specified
        if param.include:
            cmd_parts.extend(['--include', f'"{param.include}"'])
        
        # Add the pattern (properly escaped)
        pattern = f'"{param.pattern}"'
        cmd_parts.append(pattern)
        
        # Add the path (default to current directory)
        if param.path:
            path = os.path.join(job_dir, param.path) if not os.path.isabs(param.path) else param.path
        else:
            path = job_dir
        
        cmd_parts.append(path)
        
        # Join the command parts
        cmd = ' '.join(cmd_parts)
        
        bash_ops = BashOps(cmd=cmd)
        
        try:
            result = await sandbox.run_bash(bash_ops=bash_ops, cwd=job_dir)
            return result
        except Exception as e:
            # Grep returns exit code 1 when no matches found, which is not an error
            if "exit code 1" in str(e).lower():
                return "No matches found"
            logger.error(f"Executing grep command with exception: {e}")
            return f'Running grep command failed with exception: {e}'
    
    async def execute(self, params: GrepToolParam, context):
        # Send init message
        await self.send_init_message(
            context,
            execute_result=AgentExecuteResult(
                tool_grep_result=GrepToolResult(
                    pattern=params.pattern,
                    path=params.path or ".",
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
                tool_grep_result=GrepToolResult(
                    pattern=params.pattern,
                    path=params.path or ".",
                    result=result
                )
            )
        )
        
        return result
