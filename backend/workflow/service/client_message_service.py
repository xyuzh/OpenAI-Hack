import json
from typing import Dict, Optional

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

    async def publish_to_thread(self, thread_id: str, data: AgentExecuteData) -> str:
        """
        发布消息到线程 (使用Redis List和Pub/Sub)
        
        Args:
            thread_id: 线程ID
            data: 事件数据
            
        Returns:
            str: 消息索引
        """
        # 设置时间戳
        if data.create_at is None:
            data.create_at = arrow.utcnow().isoformat()
        if data.modify_at is None:
            data.modify_at = arrow.utcnow().isoformat()
            
        # 如果任务完成或错误，设置结束时间
        if data.current_state in [CurrentState.COMPLETE, CurrentState.ERROR]:
            if data.execute_end_at is None:
                data.execute_end_at = arrow.utcnow().isoformat()
        
        # 构建Redis键
        response_list_key = f"agent_run:{thread_id}:responses"
        response_channel = f"agent_run:{thread_id}:new_response"
        
        try:
            # 准备消息数据
            message_data = {
                "type": "task_agent_execute",
                "uuid": data.uuid,
                "data": data.model_dump(exclude_none=True),
                "timestamp": arrow.utcnow().isoformat()
            }
            
            # 检查是否需要覆盖已存在的消息（基于UUID）
            existing_messages = await self.redis.lrange(response_list_key, 0, -1)
            message_index = -1
            
            for idx, existing_msg in enumerate(existing_messages):
                try:
                    existing_data = json.loads(existing_msg)
                    if existing_data.get("uuid") == data.uuid:
                        message_index = idx
                        break
                except json.JSONDecodeError:
                    continue
            
            # 将消息序列化为JSON
            message_json = json.dumps(message_data)
            
            if message_index >= 0:
                # 覆盖已存在的消息
                await self.redis.lset(response_list_key, message_index, message_json)
                logger.debug(f"覆盖消息 UUID: {data.uuid} 在索引 {message_index}")
            else:
                # 添加新消息到列表末尾
                await self.redis.rpush(response_list_key, message_json)
                message_index = await self.redis.llen(response_list_key) - 1
                logger.debug(f"添加新消息 UUID: {data.uuid} 到索引 {message_index}")
            
            # 设置列表过期时间（24小时）
            await self.redis.expire(response_list_key, 86400)
            
            # 发布通知到频道
            await self.redis.publish(response_channel, "new")
            logger.debug(f"发布通知到频道: {response_channel}")
            
            return str(message_index)
            
        except Exception as e:
            logger.error(f"发布消息到线程 {thread_id} 失败: {e}")
            raise

    async def publish_control_signal(self, thread_id: str, signal: str) -> None:
        """
        发布控制信号到线程
        
        Args:
            thread_id: 线程ID
            signal: 控制信号 (STOP, ERROR, END_STREAM)
        """
        control_channel = f"agent_run:{thread_id}:control"
        try:
            await self.redis.publish(control_channel, signal)
            logger.info(f"发布控制信号 '{signal}' 到线程 {thread_id}")
        except Exception as e:
            logger.error(f"发布控制信号失败: {e}")
            raise

    async def stream_and_save_response(self, flow_uuid: str, flow_input_uuid: str, event: EventStreamSseEvent,
                                       data: AgentExecuteData) -> str:
        """
        保持向后兼容的方法 - 将调用转发到thread-based方法
        
        Args:
            flow_uuid: 流程UUID (作为thread_id)
            flow_input_uuid: 流程输入UUID (忽略)
            event: 事件类型
            data: 事件数据
            
        Returns:
            str: 消息索引
        """
        # 使用flow_uuid作为thread_id
        thread_id = flow_uuid
        
        # 如果任务完成或错误，保存结果
        if data.current_state in [CurrentState.COMPLETE, CurrentState.ERROR]:
            try:
                await save_task_agent_result(flow_uuid, flow_input_uuid, data)
            except Exception as e:
                logger.error(f"保存任务结果失败: {e}")
                # 继续处理，不中断流程
        
        # 发布到线程
        return await self.publish_to_thread(thread_id, data)

    async def stream_and_save_response_thread(self, thread_id: str, run_id: str, 
                                             data: AgentExecuteData) -> str:
        """
        线程模式的消息发布
        
        Args:
            thread_id: 线程ID
            run_id: 运行ID
            data: 事件数据
            
        Returns:
            str: 消息索引
        """
        # 如果任务完成或错误，保存结果
        if data.current_state in [CurrentState.COMPLETE, CurrentState.ERROR]:
            try:
                # 在线程模式下，使用thread_id和run_id保存
                await save_task_agent_result(thread_id, run_id, data)
            except Exception as e:
                logger.error(f"保存任务结果失败: {e}")
                # 继续处理，不中断流程
        
        # 发布到线程
        return await self.publish_to_thread(thread_id, data)