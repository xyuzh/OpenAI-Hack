# -*- coding: utf-8 -*-
"""
SSE服务
提供SSE事件流生成和管理功能
"""
import asyncio
import json
from typing import AsyncGenerator, Optional, Union, Any, Dict, Tuple

import arrow
from pydantic import BaseModel

from common.config import Config
from common.db.redis_pool import get_async_redis_client
from common.type.sse import EventStreamSseEvent
from common.utils.logger_utils import get_logger

logger = get_logger("gateway.service.agent_event_stream_service")


# ==================== 自定义异常类 ====================

class StreamServiceException(Exception):
    """Stream服务基础异常"""
    pass


class StreamConnectionException(StreamServiceException):
    """Stream连接异常 - 需要断开连接的异常"""
    pass


class StreamTimeoutException(StreamConnectionException):
    """Stream超时异常"""
    pass


class StreamRedisException(StreamConnectionException):
    """Redis连接异常"""
    pass


class StreamClientDisconnectedException(StreamConnectionException):
    """客户端断开连接异常"""
    pass


class StreamBusinessException(StreamServiceException):
    """业务逻辑异常 - 可以继续连接但需要发送错误事件"""
    pass


# ==================== 数据模型 ====================

class WaitingEventData(BaseModel):
    """等待事件数据模型"""
    time: str


class KeepAliveEventData(BaseModel):
    """保活事件数据模型"""
    time: str


class ErrorEventData(BaseModel):
    """错误事件数据模型"""
    error: str
    error_type: Optional[str] = None


class SseEventMessage(BaseModel):
    """SSE事件消息模型"""
    event_type: EventStreamSseEvent | str
    data: Union[WaitingEventData, KeepAliveEventData, ErrorEventData, Dict[str, Any]]

    def format_as_sse(self) -> str:
        """格式化为SSE消息格式"""
        if isinstance(self.data, BaseModel):
            json_data = self.data.model_dump_json()
        else:
            json_data = json.dumps(self.data, ensure_ascii=False)

        if isinstance(self.event_type, EventStreamSseEvent):
            return f"event: {self.event_type.value}\ndata: {json_data}\n\n"
        else:
            return f"event: {self.event_type}\ndata: {json_data}\n\n"

    def is_business_message(self) -> bool:
        """判断是否为业务消息（非系统消息）"""
        if isinstance(self.event_type, EventStreamSseEvent):
            return self.event_type not in [
                EventStreamSseEvent.WAITING,
                EventStreamSseEvent.KEEP_ALIVE,
                EventStreamSseEvent.ERROR
            ]
        else:
            # 字符串类型的事件类型，排除系统消息
            system_events = ["waiting", "keep_alive", "error", "ping", "heartbeat"]
            return self.event_type.lower() not in system_events


# ==================== 配置类 ====================

class StreamConfig:
    """
    Stream配置类

    配置项说明：
    - event_source_stream_prefix: Redis Stream键名前缀
    - event_source_max_stream_length: Stream最大长度
    - event_source_stream_read_count: 每次读取的消息数量
    - event_source_stream_block_time_ms: 阻塞读取超时时间(毫秒)
    - event_source_keep_alive_interval: 保活消息发送间隔(秒)
    - event_source_message_queue_max_size: 内存消息队列最大大小
    - event_source_timeout_minutes: 业务消息超时时间(分钟) - 用于以下场景：
        * 等待Stream创建的最大时间
        * 业务消息监听无数据的超时时间（keep-alive等系统消息不重置此超时）
        推荐值: 2-5分钟，根据业务场景调整
    - event_source_stream_check_interval_seconds: Stream创建检查间隔(秒)
        推荐值: 1-3秒，避免过于频繁的检查
    - event_source_connection_max_duration_minutes: 连接最大存活时间(分钟)
        绝对超时时间，无论是否有消息，连接最多存活这么长时间
        推荐值: 30-60分钟，防止连接无限期存活
    """

    # Redis Stream的起始ID常量
    STREAM_START_ID = "0-0"

    def __init__(self):
        """初始化配置"""
        event_source_config = Config.get_event_source_config()

        # Redis Stream配置
        self.stream_prefix = event_source_config['event_source_stream_prefix']
        self.max_stream_length = int(event_source_config['event_source_max_stream_length'])
        self.stream_read_count = int(event_source_config['event_source_stream_read_count'])
        self.stream_block_time_ms = int(event_source_config['event_source_stream_block_time_ms'])

        # 业务配置
        self.keep_alive_interval = int(event_source_config['event_source_keep_alive_interval'])
        self.message_queue_max_size = int(event_source_config['event_source_message_queue_max_size'])

        # 业务消息超时配置 - 用于业务消息等待的场景
        self.timeout_minutes = int(event_source_config['event_source_timeout_minutes'])

        # 连接绝对超时配置 - 防止连接无限期存活
        self.connection_max_duration_minutes = int(
            event_source_config['event_source_connection_max_duration_minutes']
        )

        # Stream创建检查间隔（秒）
        self.stream_check_interval_seconds = int(event_source_config['event_source_stream_check_interval_seconds'])

        # 连接超时检查间隔（秒）
        self.connection_timeout_check_interval_seconds = int(event_source_config['event_source_connection_timeout_check_interval_seconds'])


# ==================== Redis Stream读取器 ====================

class RedisStreamReader:
    """Redis Stream读取器"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.redis = None

    async def ensure_connection(self) -> None:
        """确保Redis连接可用，失败时抛出异常"""
        if self.redis is None:
            logger.warning("Redis连接不可用，尝试重新连接")
            try:
                self.redis = await get_async_redis_client()
                await self.redis.ping()
                logger.info("Redis重新连接成功")
            except Exception as e:
                logger.error(f"Redis重新连接失败: {e}")
                raise StreamRedisException(f"无法连接到Redis: {e}")

    def _get_stream_key(self, flow_uuid: str, flow_input_uuid: str) -> str:
        """获取Stream键名"""
        return f"{self.config.stream_prefix}.{flow_uuid}.{flow_input_uuid}"

    async def check_stream_exists(self, flow_uuid: str, flow_input_uuid: str) -> bool:
        """检查Stream是否存在"""
        await self.ensure_connection()

        stream_key = self._get_stream_key(flow_uuid, flow_input_uuid)
        if self.redis is None:
            raise StreamRedisException("Redis连接不可用")

        try:
            return await self.redis.exists(stream_key)
        except Exception as e:
            logger.error(f"检查Stream存在性失败: {e}")
            raise StreamRedisException(f"检查Stream失败: {e}")

    async def wait_for_stream_creation(self, flow_uuid: str, flow_input_uuid: str) -> bool:
        """
        等待Stream创建，使用统一的超时时间

        Args:
            flow_uuid: 流程UUID
            flow_input_uuid: 流程输入UUID

        Returns:
            bool: Stream是否创建成功

        Raises:
            StreamTimeoutException: 等待超时时抛出异常
        """
        start_time = arrow.utcnow()
        timeout_seconds = self.config.timeout_minutes * 60

        logger.info(f"开始等待Stream创建: {flow_uuid}.{flow_input_uuid}, 超时时间: {self.config.timeout_minutes}分钟")

        while True:
            # 检查是否已经创建
            if await self.check_stream_exists(flow_uuid, flow_input_uuid):
                elapsed_time = (arrow.utcnow() - start_time).total_seconds()
                logger.info(f"Stream创建成功: {flow_uuid}.{flow_input_uuid}, 等待时间: {elapsed_time:.1f}秒")
                return True

            # 检查是否超时
            elapsed_time = (arrow.utcnow() - start_time).total_seconds()
            if elapsed_time >= timeout_seconds:
                error_msg = f"等待Stream创建超时: {flow_uuid}.{flow_input_uuid}, 已等待{self.config.timeout_minutes}分钟"
                logger.error(error_msg)
                raise StreamTimeoutException(error_msg)

            # 等待一段时间后重试
            await asyncio.sleep(self.config.stream_check_interval_seconds)

    async def fetch_messages(
            self,
            flow_uuid: str,
            flow_input_uuid: str,
            start_id: Optional[str] = None,
            block_ms: Optional[int] = None
    ) -> Tuple[list, str]:
        """
        统一的消息获取方法

        Args:
            flow_uuid: 流程UUID
            flow_input_uuid: 流程输入UUID  
            start_id: 起始消息ID，None表示从头开始
            block_ms: 阻塞时间(毫秒)，None表示非阻塞模式

        Returns:
            Tuple[list, str]: (消息列表, 下一个读取位置的ID)

        Raises:
            StreamRedisException: Redis连接或操作异常
        """
        await self.ensure_connection()

        stream_key = self._get_stream_key(flow_uuid, flow_input_uuid)

        try:
            if self.redis is None:
                raise StreamRedisException("Redis连接不可用")

            # 检查Stream是否存在
            if not await self.redis.exists(stream_key):
                return [], start_id or self.config.STREAM_START_ID

            # 确定实际的起始ID
            actual_start_id = start_id or self.config.STREAM_START_ID

            # 根据是否阻塞选择不同的读取方式
            if block_ms is None:
                # 非阻塞模式：使用xrange获取历史消息
                messages = await self.redis.xrange(
                    stream_key,
                    min=actual_start_id,
                    max='+',
                    count=self.config.stream_read_count
                )
            else:
                # 阻塞模式：使用xread等待新消息
                streams = {stream_key: actual_start_id}
                result = await self.redis.xread(
                    streams=streams,  # type: ignore
                    count=self.config.stream_read_count,
                    block=block_ms
                )
                # xread返回的格式为 {stream_key: [(id, data), ...]}
                messages = dict(result).get(stream_key, []) if result else []

            # 如果start_id不是起始ID且结果中包含start_id，需要排除它（避免重复）
            if (actual_start_id != self.config.STREAM_START_ID and
                    messages and messages[0][0] == actual_start_id):
                messages = messages[1:]

            # 计算下一个读取位置
            next_id = messages[-1][0] if messages else actual_start_id

            return messages, next_id

        except Exception as e:
            logger.error(f"获取Stream消息失败: {e}")
            raise StreamRedisException(f"获取消息失败: {e}")


# ==================== 事件消息工厂 ====================

class EventMessageFactory:
    """事件消息工厂类"""

    @staticmethod
    def create_waiting_event() -> SseEventMessage:
        """创建等待事件"""
        return SseEventMessage(
            event_type=EventStreamSseEvent.WAITING,
            data=WaitingEventData(time=arrow.utcnow().isoformat())
        )

    @staticmethod
    def create_keep_alive_event() -> SseEventMessage:
        """创建保活事件"""
        return SseEventMessage(
            event_type=EventStreamSseEvent.KEEP_ALIVE,
            data=KeepAliveEventData(time=arrow.utcnow().isoformat())
        )

    @staticmethod
    def create_error_event(error_msg: str, error_type: Optional[str] = None) -> SseEventMessage:
        """创建错误事件"""
        return SseEventMessage(
            event_type=EventStreamSseEvent.ERROR,
            data=ErrorEventData(error=error_msg, error_type=error_type)
        )

    @staticmethod
    def create_task_agent_execute_event(data: Dict[str, Any]) -> SseEventMessage:
        """创建任务代理执行事件"""
        return SseEventMessage(
            event_type=EventStreamSseEvent.TASK_AGENT_EXECUTE,
            data=data
        )

    @staticmethod
    def parse_redis_message(msg_data: Dict[str, Any]) -> SseEventMessage:
        """
        解析Redis消息并创建相应的事件

        Raises:
            StreamBusinessException: 消息解析失败时抛出业务异常
        """
        if 'event' not in msg_data or 'data' not in msg_data:
            error_msg = f"Redis消息格式不完整: {msg_data}"
            logger.warning(error_msg)
            raise StreamBusinessException(error_msg)

        event_type_str = msg_data['event']
        data_str = msg_data['data']

        try:
            # 解析data字段的JSON内容
            data_json = json.loads(data_str)

            # 创建对应的事件消息
            return SseEventMessage(
                event_type=event_type_str,
                data=data_json
            )
        except json.JSONDecodeError as e:
            error_msg = f"Redis消息JSON解析失败: {data_str}, 错误: {e}"
            logger.error(error_msg)
            raise StreamBusinessException(error_msg)


# ==================== 超时管理器 ====================

class TimeoutManager:
    """超时管理器，负责管理连接的各种超时逻辑"""

    def __init__(self, config: StreamConfig, flow_uuid: str, flow_input_uuid: str):
        self.config = config
        self.flow_uuid = flow_uuid
        self.flow_input_uuid = flow_input_uuid

        # 连接开始时间
        self.connection_start_time = arrow.utcnow()

        # 最后一条业务消息时间（初始化为连接开始时间）
        self.last_business_message_time = self.connection_start_time

        # 最后一条任意消息时间（用于日志记录）
        self.last_any_message_time = self.connection_start_time

    def update_business_message_time(self) -> None:
        """更新最后一条业务消息的时间"""
        self.last_business_message_time = arrow.utcnow()
        self.last_any_message_time = arrow.utcnow()
        logger.debug(f"更新业务消息时间: {self.flow_uuid}.{self.flow_input_uuid}")

    def update_any_message_time(self) -> None:
        """更新最后一条任意消息的时间（包括系统消息）"""
        self.last_any_message_time = arrow.utcnow()

    def check_business_timeout(self) -> None:
        """
        检查业务消息超时

        Raises:
            StreamTimeoutException: 业务消息超时时抛出异常
        """
        current_time = arrow.utcnow()
        time_since_last_business = (current_time - self.last_business_message_time).total_seconds()

        if time_since_last_business > self.config.timeout_minutes * 60:
            error_msg = (f"Stream {self.flow_uuid}.{self.flow_input_uuid} "
                         f"超过{self.config.timeout_minutes}分钟没有收到业务消息，连接超时")
            logger.warning(f"业务消息超时: {error_msg}")
            raise StreamTimeoutException(error_msg)

    def check_connection_timeout(self) -> None:
        """
        检查连接绝对超时

        Raises:
            StreamTimeoutException: 连接绝对超时时抛出异常
        """
        current_time = arrow.utcnow()
        connection_duration = (current_time - self.connection_start_time).total_seconds()

        if connection_duration > self.config.connection_max_duration_minutes * 60:
            error_msg = (f"Stream {self.flow_uuid}.{self.flow_input_uuid} "
                         f"连接已存活{self.config.connection_max_duration_minutes}分钟，达到最大存活时间")
            logger.warning(f"连接绝对超时: {error_msg}")
            raise StreamTimeoutException(error_msg)

    def get_timeout_status(self) -> Dict[str, Any]:
        """获取超时状态信息，用于日志记录"""
        current_time = arrow.utcnow()
        return {
            "connection_duration_seconds": (current_time - self.connection_start_time).total_seconds(),
            "time_since_last_business_message": (current_time - self.last_business_message_time).total_seconds(),
            "time_since_last_any_message": (current_time - self.last_any_message_time).total_seconds(),
            "business_timeout_threshold": self.config.timeout_minutes * 60,
            "connection_timeout_threshold": self.config.connection_max_duration_minutes * 60
        }


# ==================== 主服务类 ====================

class AgentEventStreamService:
    """SSE服务类，处理LLM流式内容的SSE转发"""

    def __init__(self):
        """初始化SSE服务"""
        self.config = StreamConfig()
        self.stream_reader = RedisStreamReader(self.config)
        self.initialized = False

        logger.info("AgentEventStreamService初始化完成")

    async def initialize(self):
        """初始化服务的异步资源"""
        if not self.initialized:
            try:
                # 初始化Redis连接
                await self.stream_reader.ensure_connection()
                self.initialized = True
                logger.info("AgentEventStreamService异步资源初始化完成")
            except Exception as e:
                logger.error(f"AgentEventStreamService初始化失败: {e}")
                raise StreamRedisException(f"服务初始化失败: {e}")
        return self

    async def close(self):
        """关闭服务资源"""
        self.stream_reader.redis = None
        self.initialized = False
        logger.info("AgentEventStreamService资源已关闭")

    async def _check_client_connection(self, request) -> None:
        """检查客户端连接状态，断开时抛出异常"""
        if await request.is_disconnected():
            raise StreamClientDisconnectedException("客户端已断开连接")

    async def _keep_alive_timer(self, message_queue: asyncio.Queue, flow_uuid: str, flow_input_uuid: str):
        """保活定时器任务"""
        try:
            while True:
                await asyncio.sleep(self.config.keep_alive_interval)

                # 创建保活事件
                keep_alive_event = EventMessageFactory.create_keep_alive_event()

                try:
                    # 非阻塞方式放入队列
                    message_queue.put_nowait(keep_alive_event)
                    logger.debug(f"发送keep alive消息: {flow_uuid}.{flow_input_uuid}")
                except asyncio.QueueFull:
                    logger.warning(f"消息队列已满，跳过keep alive消息: {flow_uuid}.{flow_input_uuid}")

        except asyncio.CancelledError:
            logger.debug(f"Keep alive定时器被取消: {flow_uuid}.{flow_input_uuid}")
            raise
        except Exception as e:
            logger.error(f"Keep alive定时器异常: {e}")
            # 保活定时器的异常不应该中断整个流，记录日志即可

    async def _timeout_checker(
            self,
            timeout_manager: TimeoutManager,
            request,
            flow_uuid: str,
            flow_input_uuid: str
    ):
        """
        超时检查任务，定期检查各种超时条件

        Raises:
            StreamTimeoutException: 超时异常
            StreamClientDisconnectedException: 客户端断开连接
        """
        try:
            logger.info(f"启动超时检查器: {flow_uuid}.{flow_input_uuid}, 检查间隔: {self.config.connection_timeout_check_interval_seconds}秒")

            while True:
                await asyncio.sleep(self.config.connection_timeout_check_interval_seconds)

                # 检查客户端连接状态
                await self._check_client_connection(request)

                # 检查业务消息超时
                timeout_manager.check_business_timeout()

                # 检查连接绝对超时
                timeout_manager.check_connection_timeout()

                # 记录超时状态（debug级别，避免日志过多）
                status = timeout_manager.get_timeout_status()
                logger.debug(f"超时状态检查: {flow_uuid}.{flow_input_uuid} - {status}")

        except asyncio.CancelledError:
            logger.debug(f"超时检查器被取消: {flow_uuid}.{flow_input_uuid}")
            raise
        except (StreamTimeoutException, StreamClientDisconnectedException):
            # 这些异常需要中断连接，直接向上传播
            raise
        except Exception as e:
            logger.error(f"超时检查器发生未预期异常: {e}")
            # 其他未预期的异常也应该中断连接
            raise StreamRedisException(f"超时检查器异常: {e}")

    async def _redis_message_listener(
            self,
            message_queue: asyncio.Queue,
            request,
            flow_uuid: str,
            flow_input_uuid: str,
            current_id: str,
            timeout_manager: TimeoutManager
    ):
        """
        Redis消息监听任务

        Raises:
            StreamClientDisconnectedException: 客户端断开连接
            StreamRedisException: Redis操作异常
        """
        try:
            logger.info(f"开始监听Redis消息: {flow_uuid}.{flow_input_uuid}, 起始ID: {current_id}")

            listening_id = current_id

            while True:
                # 检查客户端连接状态
                await self._check_client_connection(request)

                # 获取新消息（阻塞模式）
                new_messages, next_id = await self.stream_reader.fetch_messages(
                    flow_uuid, flow_input_uuid, listening_id, block_ms=self.config.stream_block_time_ms
                )

                # 再次检查客户端连接状态
                await self._check_client_connection(request)

                if new_messages:
                    # 更新监听ID
                    listening_id = next_id

                    logger.debug(
                        f"收到{len(new_messages)}条新消息: {flow_uuid}.{flow_input_uuid}, 新的监听ID: {listening_id}")

                    # 处理新消息
                    for msg_id, msg_data in new_messages:
                        try:
                            event_message = EventMessageFactory.parse_redis_message(msg_data)

                            # 更新超时管理器的消息时间
                            if event_message.is_business_message():
                                timeout_manager.update_business_message_time()
                                logger.debug(f"收到业务消息，更新业务消息时间: {flow_uuid}.{flow_input_uuid}")
                            else:
                                timeout_manager.update_any_message_time()
                                logger.debug(f"收到系统消息: {flow_uuid}.{flow_input_uuid}")

                            try:
                                message_queue.put_nowait(event_message)
                            except asyncio.QueueFull:
                                logger.warning(f"消息队列已满，跳过Redis消息: {flow_uuid}.{flow_input_uuid}")

                        except StreamBusinessException as e:
                            # 业务异常转换为错误事件继续发送
                            logger.warning(f"消息解析失败，发送错误事件: {e}")
                            error_event = EventMessageFactory.create_error_event(str(e), "parse_error")
                            try:
                                message_queue.put_nowait(error_event)
                            except asyncio.QueueFull:
                                logger.warning(f"消息队列已满，跳过错误事件: {flow_uuid}.{flow_input_uuid}")

        except asyncio.CancelledError:
            logger.debug(f"Redis消息监听器被取消: {flow_uuid}.{flow_input_uuid}")
            raise
        except (StreamClientDisconnectedException, StreamRedisException):
            # 这些异常需要中断连接，直接向上传播
            raise
        except Exception as e:
            # 其他未预期的异常也应该中断连接
            logger.error(f"Redis消息监听器发生未预期异常: {e}")
            raise StreamRedisException(f"消息监听器异常: {e}")
        finally:
            logger.info(f"Redis消息监听器结束: {flow_uuid}.{flow_input_uuid}")

    async def stream_thread_events(
            self,
            request,
            thread_id: str,
            last_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        生成线程的SSE事件流
        
        Args:
            request: FastAPI请求对象
            thread_id: 线程ID
            last_id: 上次读取的消息ID (可选)
        
        Raises:
            StreamConnectionException: 连接相关异常（超时、断开、Redis异常等）
        """
        # 对于线程模式，我们使用thread_id作为flow_uuid，使用"stream"作为flow_input_uuid
        # 这样可以保持向后兼容性
        flow_uuid = thread_id
        flow_input_uuid = "stream"
        
        async for event in self.stream_sse_events(request, flow_uuid, flow_input_uuid, last_id):
            yield event
    
    async def stream_sse_events(
            self,
            request,
            flow_uuid: str,
            flow_input_uuid: str,
            last_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        生成SSE事件流

        Raises:
            StreamConnectionException: 连接相关异常（超时、断开、Redis异常等）
        """
        try:
            # 确保服务已初始化
            await self.stream_reader.ensure_connection()

            # 检查初始连接状态
            await self._check_client_connection(request)

            # 创建超时管理器
            timeout_manager = TimeoutManager(self.config, flow_uuid, flow_input_uuid)

            logger.info(f"建立SSE连接: {flow_uuid}.{flow_input_uuid}, "
                        f"业务消息超时: {self.config.timeout_minutes}分钟, "
                        f"连接最大存活时间: {self.config.connection_max_duration_minutes}分钟")

            # 检查Stream是否存在
            stream_exists = await self.stream_reader.check_stream_exists(flow_uuid, flow_input_uuid)

            if not stream_exists:
                # 发送等待事件
                waiting_event = EventMessageFactory.create_waiting_event()
                yield waiting_event.format_as_sse()
                logger.info(f"等待流程 {flow_uuid}.{flow_input_uuid} 的消息流创建")

                # 等待Stream创建（可能抛出超时异常）
                stream_exists = await self.stream_reader.wait_for_stream_creation(flow_uuid, flow_input_uuid)

            # 处理历史消息 - 无论last_id是什么都要处理
            logger.info(f"开始处理历史消息，起始ID: {last_id or self.config.STREAM_START_ID}")

            current_id = last_id or self.config.STREAM_START_ID
            has_business_message_in_history = False

            if stream_exists:
                # 获取并发送历史消息
                messages, current_id = await self.stream_reader.fetch_messages(
                    flow_uuid, flow_input_uuid, last_id, block_ms=None
                )

                if messages:
                    logger.info(f"发送历史消息: {len(messages)}条消息")
                    for msg_id, msg_data in messages:
                        # 检查连接状态
                        await self._check_client_connection(request)

                        try:
                            event_message = EventMessageFactory.parse_redis_message(msg_data)

                            # 检查是否有业务消息
                            if event_message.is_business_message():
                                has_business_message_in_history = True

                            yield event_message.format_as_sse()
                        except StreamBusinessException as e:
                            # 历史消息解析失败，发送错误事件但继续处理
                            logger.warning(f"历史消息解析失败: {e}")
                            error_event = EventMessageFactory.create_error_event(str(e), "historical_parse_error")
                            yield error_event.format_as_sse()

            # 如果历史消息中有业务消息，更新业务消息时间
            if has_business_message_in_history:
                timeout_manager.update_business_message_time()
                logger.info(f"历史消息中包含业务消息，更新业务消息时间: {flow_uuid}.{flow_input_uuid}")

            # 创建消息队列和并发任务
            message_queue = asyncio.Queue(maxsize=self.config.message_queue_max_size)

            keep_alive_task = asyncio.create_task(
                self._keep_alive_timer(message_queue, flow_uuid, flow_input_uuid)
            )

            timeout_checker_task = asyncio.create_task(
                self._timeout_checker(timeout_manager, request, flow_uuid, flow_input_uuid)
            )

            redis_listener_task = asyncio.create_task(
                self._redis_message_listener(message_queue, request, flow_uuid, flow_input_uuid, current_id, timeout_manager)
            )

            try:
                # 监听消息队列并发送事件
                while True:
                    # 创建获取消息和检查连接状态的并行任务
                    message_task = asyncio.create_task(message_queue.get())
                    disconnect_task = asyncio.create_task(request.is_disconnected())

                    try:
                        # 等待任一任务完成
                        done, pending = await asyncio.wait(
                            [message_task, disconnect_task],
                            return_when=asyncio.FIRST_COMPLETED
                        )

                        # 取消未完成的任务
                        for task in pending:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                        # 处理完成的任务
                        for task in done:
                            if task == disconnect_task:
                                if task.result():
                                    logger.info(f"检测到客户端断开连接: {flow_uuid}.{flow_input_uuid}")
                                    raise StreamClientDisconnectedException("客户端断开连接")
                            elif task == message_task:
                                # 获取事件消息并发送
                                event_message: SseEventMessage = task.result()
                                yield event_message.format_as_sse()
                                message_queue.task_done()

                    except (StreamTimeoutException, StreamClientDisconnectedException, StreamRedisException):
                        # 连接相关异常，直接向上传播
                        raise
                    except Exception as e:
                        logger.error(f"处理消息时出现未预期错误: {e}")
                        # 取消所有任务
                        for task in [message_task, disconnect_task]:
                            if not task.done():
                                task.cancel()
                        # 将未预期错误也视为连接异常
                        raise StreamRedisException(f"消息处理异常: {e}")

            finally:
                # 清理任务
                keep_alive_task.cancel()
                timeout_checker_task.cancel()
                redis_listener_task.cancel()

                try:
                    await asyncio.gather(keep_alive_task, timeout_checker_task, redis_listener_task, return_exceptions=True)
                except Exception as e:
                    logger.error(f"清理并发任务时出错: {e}")

        except StreamConnectionException:
            # 连接相关异常直接向上传播，让FastAPI处理
            raise
        except Exception as e:
            # 其他未预期异常也转换为连接异常
            logger.error(f"SSE流处理发生未预期错误: {e}")
            raise StreamRedisException(f"流处理异常: {e}")
