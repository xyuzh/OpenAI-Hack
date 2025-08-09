from common.type.agent import AgentExecuteType, AgentExecuteResult, LsToolResult
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from workflow.tool.ls.tool import LsToolParam, LsTool
from workflow.service.schema import BashOps


@register_tool("ls_tool")
class LsToolExecutor(BaseTool):
    param_class = LsToolParam
    tool_definition = LsTool
    execute_type = AgentExecuteType.TOOL_LS

    async def _executor(self,
        sandbox: DaytonaSandbox, job_dir: str, param: LsToolParam
    ) -> str:
        # Build the tree command
        # -a shows hidden files, -F adds file type indicators, -I for ignore patterns
        cmd_parts = ['tree', '-a', '-F']
        
        # If ignore patterns are provided, add them to the tree command
        if param.ignore:
            # Tree uses -I flag with pipe-separated patterns
            ignore_pattern = '|'.join(param.ignore)
            cmd_parts.extend(['-I', f'"{ignore_pattern}"'])
        
        # Add the target path
        cmd_parts.append(param.path)
        
        # Join the command parts
        cmd = ' '.join(cmd_parts)
        
        bash_ops = BashOps(cmd=cmd)
        
        try:
            result = await sandbox.run_bash(bash_ops=bash_ops, cwd=job_dir)
            
            if len(result) > 500:
                truncated_result = result[:500]
                result = truncated_result + "\n\n[Output truncated - directory structure is large. Consider using ignore patterns to filter out unnecessary directories/files like node_modules, .git, __pycache__, etc.]"
            
            return result
        except Exception as e:
            logger.error(f"Executing ls command with exception: {e}")
            return f'Running ls command failed with exception: {e}'
    
    async def execute(self, params: LsToolParam, context):
        # Send init message
        await self.send_init_message(
            context,
            execute_result=AgentExecuteResult(
                tool_ls_result=LsToolResult(
                    path=params.path,
                    ignore=params.ignore,
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
                tool_ls_result=LsToolResult(
                    path=params.path,
                    ignore=params.ignore,
                    result=result
                )
            )
        )
        
        return result
