import os
from datetime import datetime, timezone
from litellm import ChatCompletionToolParam
from litellm.files.main import ModelResponse
from pydantic import BaseModel

from workflow.core.config import AgentConfig
from workflow.llm.llm import LLM, Model
from workflow.prompt.prompt import PromptManager
from workflow.tool.tool import AgentTools
from workflow.core.message import Message, TextContent
from workflow.schema.job_state import JobState, JobRunState
from workflow.agent.tool.plan_task import JobPlan
from workflow.core.logger import usebase_logger as logger


class Agent:
    def __init__(self, llm: LLM, config: AgentConfig):
        self.config = config
        self.llm = llm
        self.prompt_manager = PromptManager(
            prompt_dir=os.path.join(os.path.dirname(__file__), 'prompt')
        )
        self.agent_tools = AgentTools()

    async def fix_tool_call_params(self, tool_call: str, schema: BaseModel) -> dict:
        params: dict = {
            "messages": [
                {
                    "role": "system",
                    "content": 'Fix the  tool call parameters to match the schema',
                },
                {"role": "user", "content": tool_call},
            ],
            "response_format": schema,
        }
        resp = await self.llm.completion(**params, model=Model.gpt_4_1)
        return resp.choices[0].message.content

    def init_pre_run_messages(self, job_state: JobState, user_message: Message) -> None:
        system_prompt = self.prompt_manager.load_prompt_template(
            'pre_run_system_prompt'
        ).render()
        job_state.messages = [
            Message(role="system", content=[TextContent(text=system_prompt)]),
            user_message,
        ]


    def get_running_tools_desc(self) -> str:
        return '\n'.join(
            [
                f'{tool["function"]["name"]}: {tool["function"].get("description", "")}'
                for tool in self.get_running_tools
            ]
        )

    @property
    def get_running_tools(self) -> list[ChatCompletionToolParam]:
        return []

    @property
    def get_planning_tools(self) -> list[ChatCompletionToolParam]:
        return []

    async def step(self, job_state: JobState) -> ModelResponse:
        try:
            if job_state.state == JobRunState.NOT_STARTED:
                tools = self.get_planning_tools
                model = Model.sonnet_3_7
            elif job_state.state == JobRunState.RUNNING:
                tools = self.get_running_tools
                model = Model.sonnet_3_7
            else:
                logger.error(
                    f"Invalid job state id: {job_state.id}, state: {job_state.state}"
                )
                raise Exception(
                    f"Invalid job state: {job_state.state}, id: {job_state.id}"
                )

            params: dict = {
                "messages": self.llm.format_messages_for_llm(job_state.messages),
                "tools": tools,
                "tool_choice": "auto",
            }

            # TODO(LITE_LLM_META_DATA_PROXY): add meta data proxy
            resp = await self.llm.completion(**params, model=model, reasoning_effort='medium')
            return resp.choices[0].message
        except Exception as e:
            logger.error(f"Error during agent step: {e}")
            raise e
