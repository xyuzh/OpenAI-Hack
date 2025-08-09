import os
from workflow.tool.app_serving.tool import UrlExposeParam, UrlExposeTool
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from common.type.agent import AgentExecuteType, AgentExecuteResult, SandboxInfo
from common.utils.string_utils import generate_uuid
from common.type.domain import DomainType
from common.type.agent import AgentExecuteData, CurrentState

@register_tool("expose_app_url")
class UrlExposeToolExecutor(BaseTool):
    param_class = UrlExposeParam
    tool_definition = UrlExposeTool
    execute_type = AgentExecuteType.STATUS_SANDBOX_INFO

    async def execute(self, params: UrlExposeParam, context):
        # No init message for URL expose
        
        if context.daytona is None or context.daytona.sandbox is None:
            raise ValueError("Daytona sandbox is not available")
        
        link = await context.daytona.sandbox.get_preview_link(params.port)
        sandbox_id = context.daytona.sandbox.id
        sandbox_url = link.url
        
        # Send complete message with sandbox info
        await context.on_client_message(
            data=AgentExecuteData(
                uuid=generate_uuid(DomainType.TASK_AGENT_EXECUTE),
                current_state=CurrentState.COMPLETE,
                error_flag=False,
                execute_type=AgentExecuteType.STATUS_SANDBOX_INFO,
                execute_result=AgentExecuteResult(
                    status_sandbox_info=SandboxInfo(
                        sandbox_id=sandbox_id,
                        sandbox_url=sandbox_url,
                        app_path=os.path.join(context.job_dir, params.app_folder),
                    ),
                ),
            )
        )
        
        logger.info(f"App {params.app_folder} is running at {sandbox_url}")
        return ''



