import asyncio
import json
import pydantic
import time
from redis.asyncio import Redis
import queue
from typing import Any, Coroutine, Optional
from threading import Event
from functools import partial

from modem.type.flow_type import ProcessFlowDataRequest

from common.config.config import Config
from common.type.sse import EventStreamSseEvent
from common.type.agent import AgentExecuteData, AgentExecuteResult
from common.type.constant import CurrentState
from common.type.domain import DomainType
from common.type.agent import AgentExecuteType
from common.utils.string_utils import generate_uuid

from workflow.tool.executor import ToolExecutor
from workflow.service.client_message_service import ClientMessageService
from workflow.core.logger import usebase_logger as logger
from workflow.core.config import AppConfig
from workflow.core.message import Message, TextContent
from workflow.service.exa import ExaService
from workflow.agent.agent import Agent
from workflow.llm.llm import LLM
from workflow.schema import User
from workflow.schema.job_state import JobState, JobRunState
from workflow.core.config.utils import load_app_config
from workflow.service.app_sync_service import ReceivedMessage
from workflow.storage.job_state_repo import JobStateRepo
from workflow.storage.user_repo import UserRepo

# Rebuild agent models to resolve forward references
from common.type.agent import rebuild_models
rebuild_models()

# Suppress Pydantic serialization warnings from LiteLLM library


class Runner:
    agent: Agent
    config: AppConfig

    def __init__(self, config: AppConfig):
        agent_config = config.get_agent_config(config.default_agent)
        llm_config = config.get_llm_config_from_agent(config.default_agent)

        self.llm = LLM(config=llm_config)
        self.agent = Agent(
            llm=self.llm,
            config=agent_config,
        )
        self.config = config
        # Sandbox no longer needed - removed Daytona/E2B
        self.exa = ExaService()
        # self.appsync_service: AppSyncReceiveMessageService | None = None
        self.shutdown_event = Event()
        self.job_state_repo = JobStateRepo()
        self.user_repo = UserRepo()
        self.user: User | None = None
        self.job_state: JobState | None = None
        self.client_message_service: ClientMessageService | None = None
        self.on_client_message: partial[Coroutine[Any, Any, str]] | None = None
        self.redis_client: Redis | None = None
        self.is_local = False

    @classmethod
    async def init(cls, user_request: ProcessFlowDataRequest, is_local: bool = False):
        config = load_app_config()
        appsync_config = config.get_appsync_config()
        self = cls(config)
        self.is_local = is_local

        # init redis
        # 不再使用全局连接池，而是为每个任务创建新的 Redis 客户端
        redis_config = Config.get_redis_config()
        self.redis_client = Redis(
            host=redis_config['redis_host'],
            port=redis_config['redis_port'],
            username=redis_config.get('redis_username', None),
            password=redis_config['redis_password'],
            db=redis_config['redis_db'],
            decode_responses=True,
            max_connections=10, 
        )

        self.client_message_service = ClientMessageService(self.redis_client)

        # init on_client_message
        # Determine if we're in thread mode or legacy flow mode
        if hasattr(user_request, 'thread_id') and user_request.thread_id:
            # Thread mode - use thread_id
            thread_id = user_request.thread_id
            run_id = user_request.run_id or user_request.flow_input_uuid
        else:
            # Legacy mode - use flow_uuid as thread_id
            thread_id = user_request.flow_uuid
            run_id = user_request.flow_input_uuid
        
        if is_local:
            async def test_on_client_message(data: AgentExecuteData) -> str:
                return "test"

            self.on_client_message = test_on_client_message
        else:
            self.on_client_message = partial(
                self.client_message_service.stream_and_save_response_thread,
                thread_id=thread_id,
                run_id=run_id,
            )

        # init user and sandbox
        self.user = await self.user_repo.gen_user(user_request.user_uuid)
        # init job state
        user_message = Message.from_raw_content(
            role='user', raw_content=user_request.context_data
        )
        logger.info(f"User message: {user_message.model_dump_json()}")
        try:
            job_state = await self.job_state_repo.gen_job_state(user_request.flow_uuid)
            if (
                job_state.state == JobRunState.PENDING
                or job_state.state == JobRunState.RUNNING
            ) and self.on_client_message:
                job_state.state = JobRunState.RUNNING
                # Daytona sandbox initialization removed - no longer needed
                pass
            job_state.messages.append(user_message)
        except Exception as e:
            job_state = JobState(id=user_request.flow_uuid)
            self.agent.init_pre_run_messages(job_state, user_message)
        self.job_state = job_state

        return self

    

    def parse_response(self, resp):
        reasoning = getattr(resp, 'reasoning_content', None)
        response = getattr(resp, 'content', None)
        tool_calls = getattr(resp, 'tool_calls', None)
        message = Message.from_llm_response(resp)
        self.job_state.messages.append(message)

        return reasoning, response, tool_calls

    async def execute(self, tool_call) -> list[TextContent] | str:
        if not self.on_client_message:
            raise Exception("on_client_message is not set")
        
        # Use the new tool executor for standard tools
        executor = ToolExecutor()
        try:
            return await executor.execute(tool_call, self)
        except Exception as e:
            logger.error(f"Error executing tool call: {e}")
            raise e

    async def run_job(self):
        if not (self.on_client_message and self.user):
            raise Exception("on_client_message is not set")
        while True:
            try:
                resp = await self.agent.step(self.job_state)
            except Exception as e:
                logger.error(f"Error generating llm response: {e}")
                raise e
            # Convert LLM response to proper Message object
            reasoning, response, tool_calls = self.parse_response(resp)
            if reasoning:
                logger.info(f"Reasoning: {reasoning}")
            if response:
                await self.on_client_message(
                    data=AgentExecuteData(
                        uuid=generate_uuid(DomainType.TASK_AGENT_EXECUTE),
                        current_state=CurrentState.COMPLETE,
                        error_flag=False,
                        execute_type=AgentExecuteType.ASSISTANT_RESPONSE,
                        execute_result=AgentExecuteResult(
                            assistant_response_result=response,
                        ),
                    )
                )
                logger.info(f"Response: {response}")
            if tool_calls:
                logger.info(
                    f'Tool call name: {tool_calls[0].function.name}\n params: {tool_calls[0].function.arguments}'
                )
                    
                try:
                    results = await asyncio.gather(
                        *[self.execute(tool_call) for tool_call in tool_calls]
                    )
                    if tool_calls[0].function.name != 'job_plan':
                        tool_call_messages = [
                            Message.from_tool_call(tool_call, result)
                            for tool_call, result in zip(tool_calls, results)
                        ]
                        self.job_state.messages.extend(tool_call_messages)
                        logger.info(
                            f"Tool call name: {tool_calls[0].function.name} \nresult: {results}"
                        )
                except pydantic.ValidationError as e:
                    logger.error(f"Tool call param validation error: {e}")
                    self.job_state.messages.append(
                        Message.from_invalid_tool_call(tool_calls[0])
                    )
                    continue
                except Exception as e:
                    logger.error(f"Error executing tool call: {e}")
                    raise e
            else:
                if self.job_state.state == JobRunState.RUNNING:
                    self.job_state.state = JobRunState.PENDING

            if self.job_state.state != JobRunState.RUNNING:
                break

    async def handle_flow_completion(self, task: asyncio.Task, thread_id: Optional[str] = None):
        if self.on_client_message is None:
            return
        if task.done():
            try:
                e = task.exception()
                if e:
                    logger.error(f"Error handling flow completion: {e}")
                    if self.job_state and self.job_state.messages[-1].role != "tool":
                        self.job_state.messages = self.job_state.messages[:-1]
                    await self.on_client_message(
                        data=AgentExecuteData(
                            uuid=generate_uuid(DomainType.TASK_AGENT_EXECUTE),
                            current_state=CurrentState.ERROR,
                            error_flag=True,
                            execute_type=AgentExecuteType.FLOW_COMPLETION,
                            execute_result=AgentExecuteResult(
                                flow_completion_message=str(e),
                            ),
                        )
                    )
                    # Send control signal for error
                    if thread_id and self.client_message_service:
                        await self.client_message_service.publish_control_signal(thread_id, "ERROR")
                else:
                    await self.on_client_message(
                        data=AgentExecuteData(
                            uuid=generate_uuid(DomainType.TASK_AGENT_EXECUTE),
                            current_state=CurrentState.COMPLETE,
                            error_flag=False,
                            execute_type=AgentExecuteType.FLOW_COMPLETION,
                        )
                    )
                    # Send control signal for completion
                    if thread_id and self.client_message_service:
                        await self.client_message_service.publish_control_signal(thread_id, "END_STREAM")
            except BaseException as e:
                logger.error(f"Flow interrupted: {e}")
                await self.on_client_message(
                    data=AgentExecuteData(
                        uuid=generate_uuid(DomainType.TASK_AGENT_EXECUTE),
                        current_state=CurrentState.COMPLETE,
                        error_flag=False,
                        execute_type=AgentExecuteType.FLOW_COMPLETION,
                    )
                )
                # Send control signal for interruption
                if thread_id and self.client_message_service:
                    await self.client_message_service.publish_control_signal(thread_id, "STOP")
        

        # Save job state
        await self.job_state_repo.save(self.job_state)
        # Delete sandbox
        # Daytona cleanup removed - no longer needed
        pass
        # if self.appsync_service:
        #     self.appsync_service.close()
        if self.redis_client:
            await self.redis_client.aclose()

        # Give user failure result based on task result

    @staticmethod
    def run_flow(request: ProcessFlowDataRequest):
        async def async_run_flow() -> None:
            """Bridges blocking user_input_queue.get() into the async world."""
            task: asyncio.Task | None = None
            try:
                runner = await Runner.init(request)
                # Get thread_id for control signals
                thread_id = request.thread_id if hasattr(request, 'thread_id') and request.thread_id else request.flow_uuid
                
                task = asyncio.create_task(runner.run_job())
                while not runner.shutdown_event.is_set():
                    if task.done():
                        # TODO Exception handling and release resources
                        break
                    await asyncio.sleep(1)
            except BaseException as e:
                logger.error(f"Error running flow: {e}")
                raise e
            finally:
                if task and runner:
                    task.cancel()
                    try:
                        await task
                    except BaseException as e:
                        pass
                    await runner.handle_flow_completion(task, thread_id)

        asyncio.run(async_run_flow())

    @staticmethod
    def run_local(
        user_input_queue: queue.Queue,
        job_output_queue: queue.Queue,
        shutdown_event: Event,
    ):
        start_time = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def dispatcher() -> None:
            """Bridges blocking user_input_queue.get() into the async world."""
            cur_task: asyncio.Task | None = None
            runner: Runner | None = None
            try:
                while not shutdown_event.is_set():
                    if cur_task and runner and cur_task.done():
                        await runner.handle_flow_completion(task=cur_task)
                        duration = time.time() - start_time
                        logger.info(f"run_local completed in {duration:.2f} seconds")
                        cur_task = None
                        runner = None

                    try:
                        item = await loop.run_in_executor(
                            None, user_input_queue.get, True, 1
                        )
                        if item is None:
                            break
                        if cur_task and runner:
                            cur_task.cancel()
                            try:
                                await cur_task
                            except BaseException as e:
                                pass
                            finally:
                                await runner.handle_flow_completion(task=cur_task)

                        if item.context_data[0]['content'] != "stop":
                            runner = await Runner.init(item, is_local=True)
                            task = loop.create_task(runner.run_job())
                            cur_task = task
                            user_input_queue.task_done()

                    except queue.Empty:
                        await asyncio.sleep(1)
                        continue
            finally:
                # ----------- CANCEL *EVERYTHING* STILL RUNNING -------------
                if cur_task and runner:
                    cur_task.cancel()
                    try:
                        await cur_task
                    finally:
                        await runner.handle_flow_completion(task=cur_task)
                loop.stop()

        # start bridge coroutine and run the loop forever
        loop.create_task(dispatcher())
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
