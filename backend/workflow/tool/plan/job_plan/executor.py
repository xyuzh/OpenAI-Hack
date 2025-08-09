import os

from workflow.tool.plan.job_plan.tool import JobPlanParam, JobPlanTool
from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.core.logger import usebase_logger as logger
from workflow.prompt.prompt import PromptManager
from workflow.agent.tool.plan_task import JobPlan
from workflow.schema.job_state import JobState, JobRunState
from workflow.core.message import Message, TextContent
from workflow.service.schema import BashOps
from workflow.tool.base import BaseTool
from workflow.tool.registry import register_tool
from common.type.agent import AgentExecuteType, AgentExecuteResult


def _job_run_init(job_state: JobState):
    if job_state.job_plan is None:
        raise Exception("Job plan is not set")
    prompt_manager = PromptManager(
        prompt_dir=os.path.join(os.path.dirname(__file__), 'prompt')
    )
    system_prompt = prompt_manager.load_prompt_template(
        'job_run_system_prompt'
    ).render()
    user_prompt = prompt_manager.load_prompt_template('job_run_user_prompt').render(
        plan=job_state.job_plan.plan,
    )

    job_state.messages = [
        Message(role="system", content=[TextContent(text=system_prompt)]),
        Message(role="user", content=[TextContent(text=user_prompt)]),
    ]


async def _execute(
    job_state: JobState,
    param: JobPlanParam,
    daytona: DaytonaSandbox,
) -> None:
    try:
        job_state.job_plan = JobPlan(
            name=param.name,
            plan=param.actionable_plan,
        )
        
        # Reinitialize the message window based on the job plan
        _job_run_init(job_state)
        
        # create job dir
        await daytona.run_bash(
            bash_ops=BashOps(cmd=f'mkdir -p {job_state.job_dir}'), cwd='/'
        )
    except Exception as e:
        logger.error(f"Error executing job plan: {e}")
        raise e


@register_tool("job_plan")
class JobPlanToolExecutor(BaseTool):
    param_class = JobPlanParam
    tool_definition = JobPlanTool
    execute_type = AgentExecuteType.TOOL_JOB_PLAN

    async def execute(self, params: JobPlanParam, context):
        # Send init message
        await self.send_init_message(context)
        try:
            # Initialize Daytona
            context.daytona = await DaytonaSandbox.init(
                user=context.user,
                daytona_image=context.config.daytona_image,
                user_repo=context.user_repo,
            )

            # Update job state
            context.job_state.state = JobRunState.RUNNING

            await _execute(
                context.job_state,
                params,
                context.daytona,
            )
        except Exception as e:
            logger.error(f"Error initializing job plan: {e}")
            raise e

        # Send complete message
        await self.send_complete_message(
            context,
            execute_result=AgentExecuteResult(
                tool_job_plan_result=context.job_state.job_plan,
            ),
        )

        return "Job planned successfully"
