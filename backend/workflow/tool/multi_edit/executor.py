import os
import json
import shlex
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.tool.multi_edit.tool import MultiEditParam, MultiEditTool, EditOperation
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from common.type.agent import AgentExecuteType, AgentExecuteResult
from workflow.service.schema import BashOps


@register_tool("multi_edit")
class MultiEditToolExecutor(BaseTool):
    param_class = MultiEditParam
    tool_definition = MultiEditTool
    execute_type = AgentExecuteType.TOOL_MULTI_EDIT

    async def _executor(self, multi_edit_param: MultiEditParam, daytona: DaytonaSandbox, job_dir: str):
        try:
            # Build the bash command to call multiedit_perl
            cmd_parts = ["multi_edit", shlex.quote(multi_edit_param.file_path)]
            
            # Add each edit operation as parameters
            for edit in multi_edit_param.edits:
                cmd_parts.extend([
                    shlex.quote(edit.old_string),
                    shlex.quote(edit.new_string),
                    "true" if edit.replace_all else "false"
                ])
            
            cmd = " ".join(cmd_parts)
            
            # Execute the multi-edit command
            result = await daytona.run_bash(
                bash_ops=BashOps(cmd=cmd, timeout=30),
                cwd=job_dir
            )
            
            # Check if the command succeeded
            if "Error:" in result:
                logger.error(f"Multi-edit operation failed: {result}")
                return f"Multi-edit failed: {result}"
            else:
                return f"Successfully applied edits"
            
        except Exception as e:
            logger.error(f"Error in multi-edit operation: {e}")
            return f"Error in multi-edit operation: {e}"
    
    async def execute(self, params: MultiEditParam, context):
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
                tool_multi_edit_result=params,
            )
        )
        
        return result
