import os
from common.type.agent import AgentExecuteType, AgentExecuteResult
from workflow.prompt.prompt import PromptManager
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.core.logger import usebase_logger as logger
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from workflow.tool.use_template.tool import UseTemplateParam, UseTemplateTool
from workflow.service.schema import BashOps


@register_tool("use_template")
class UseTemplateToolExecutor(BaseTool):
    param_class = UseTemplateParam
    tool_definition = UseTemplateTool
    execute_type = AgentExecuteType.TOOL_USE_TEMPLATE

    async def _executor(
        self, param: UseTemplateParam, daytona: DaytonaSandbox, job_dir: str
    ) -> str:
        prompt_manager = PromptManager(
            prompt_dir=os.path.join(os.path.dirname(__file__), 'prompt')
        )
        project_dir = os.path.join(job_dir, param.web_app_name)
        try:
            if param.web_framework == "vite":
                cmd = f'cp -r /template/vite-template {project_dir}'
                template_instruct_prompt = 'vite_instruct_prompt'
            elif param.web_framework == "nextjs":
                cmd = f'cp -r /template/nextjs_template {project_dir}'
                template_instruct_prompt = 'nextjs_instruct_prompt'
            else:
                raise ValueError(f"Invalid web framework: {param.web_framework}")

            # 1. copy template
            await daytona.run_bash(
                bash_ops=BashOps(cmd=cmd),
                cwd=job_dir,
            )
            # 2. load prompt
            template_instruct_prompt = prompt_manager.load_prompt_template(
                template_instruct_prompt
            ).render()

            return f'Project created at directory: {param.web_app_name}\n\n{template_instruct_prompt}'
        except Exception as e:
            logger.error(f"Error using template: {e}")
            raise e

    async def execute(self, params: UseTemplateParam, context):
        # Send init message
        await self.send_init_message(
            context,
            execute_params=AgentExecuteResult(
                tool_use_template_result=params,
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
                tool_use_template_result=params,
            ),
        )

        return result
