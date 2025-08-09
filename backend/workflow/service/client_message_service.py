from typing import Dict

import arrow
from redis.asyncio import Redis
from redis.typing import EncodableT

from common.config import Config
from common.service.task_agent_service import save_task_agent_result
from common.type.agent import AgentExecuteData
from common.type.constant import CurrentState
from common.type.sse import EventStreamSseEvent
from common.utils.logger_utils import get_logger

# 配置日志
logger = get_logger("workflow.service.client_service")


class ClientMessageService:
    """Client消息服务类，封装Client消息操作"""

    def __init__(self, redis_client: Redis):
        """
        初始化Client消息服务

        Args:
            redis_client: Redis客户端实例
        """
        self.redis = redis_client
        self.event_source_config = Config.get_event_source_config()
        logger.info("Client消息服务初始化完成")

    async def stream_and_save_response(self, flow_uuid: str, flow_input_uuid: str, event: EventStreamSseEvent,
                                       data: AgentExecuteData) -> str:
        """
        将内容添加到Redis Stream

        Args:
            flow_uuid: 流程UUID
            flow_input_uuid: 流程输入UUID
            event: 事件类型
            data: 事件数据

        Returns:
            str: 消息ID
        """

        if self.event_source_config is None:
            raise RuntimeError("EventSource配置未找到")

        stream_prefix = self.event_source_config['event_source_stream_prefix']

        # 转换为整数
        max_stream_length = int(
            self.event_source_config['event_source_max_stream_length'])

        # 如果创建时间未设置，则设置为当前时间
        # 注意这里设置的值，当在进行save_task_agent_result时，后端会在onCreate函数中对值进行更新
        if data.create_at is None:
            data.create_at = arrow.utcnow().isoformat()

        # 如果修改时间未设置，则设置为当前时间
        # 注意这里设置的值，当在进行save_task_agent_result时，后端会在onCreate、onModify函数中对值进行更新
        if data.modify_at is None:
            data.modify_at = arrow.utcnow().isoformat()

        # 如果任务完成或错误
        if data.current_state == CurrentState.COMPLETE or data.current_state == CurrentState.ERROR:
            # 如果任务完成时间未设置，则设置为当前时间
            if data.execute_end_at is None:
                data.execute_end_at = arrow.utcnow().isoformat()

            # 保存任务结果
            try:
                await save_task_agent_result(
                    flow_uuid, flow_input_uuid, data)
            except Exception as e:
                logger.error(f"保存任务结果失败: {e}")
                raise

        try:
            # 构建消息 - 使用正确的类型
            message: Dict[EncodableT, EncodableT] = {
                b'event': event,
                b'data': data.model_dump_json(exclude_none=True)
            }

            # 构建Stream键名
            stream_key = f"{stream_prefix}.{flow_uuid}.{flow_input_uuid}"

            # 添加到Stream
            msg_id = await self.redis.xadd(
                stream_key, message, maxlen=max_stream_length, approximate=True)
            logger.debug(
                f"添加消息到Stream {stream_key}, ID: {msg_id}, 事件: {event}, 内容: {data}")

            return str(msg_id)
        except Exception as e:
            logger.error(f"添加消息到Redis Stream失败: {e}")
            raise
