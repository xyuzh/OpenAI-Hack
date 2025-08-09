import base64
import json
import threading
import time
import uuid
from asyncio.log import logger
from typing import List, Optional

from websocket import WebSocketApp

from modem.type.flow_type import Authorization, AppSyncMessage, AppSyncEvent


class AppSyncConnection:
    """管理单个任务的AWS AppSync连接"""

    def __init__(self, http_domain: Optional[str], websocket_domain: Optional[str], api_key: Optional[str],
                 channel: str):
        # 验证必要参数
        if not all([http_domain, websocket_domain, api_key]):
            raise ValueError("AppSyncConnection初始化失败: http_domain、websocket_domain和api_key都不能为空")

        # AppSync配置
        self.HTTP_DOMAIN = http_domain
        self.REALTIME_DOMAIN = websocket_domain
        self.API_KEY = api_key

        self.channel = channel
        self.ws = None
        self.is_connected = False
        self.is_connection_ack = False
        self.connection_event = threading.Event()
        self.connection_ack_event = threading.Event()

        # 连接超时和心跳检测
        self.connection_timeout_ms = 300000  # 默认值，会从connection_ack更新
        self.last_keepalive_time = None

    def get_auth_protocol(self) -> str:
        """生成WebSocket连接的认证协议"""
        # 由于我们在初始化时已经验证了API_KEY和HTTP_DOMAIN不为None，可以进行类型断言
        api_key = self.API_KEY
        http_domain = self.HTTP_DOMAIN
        assert isinstance(api_key, str)
        assert isinstance(http_domain, str)

        authorization = Authorization(
            **{'x-api-key': api_key, 'host': http_domain}
        )

        header_json = authorization.json(by_alias=True)
        header_bytes = header_json.encode('utf-8')
        header_base64 = base64.b64encode(header_bytes).decode('utf-8')
        header_encoded = header_base64.replace('+', '-').replace('/', '_').rstrip('=')
        return f"header-{header_encoded}"

    def on_message(self, ws, message):
        """处理接收到的WebSocket消息"""
        logger.info(f"[{self.channel}] 收到消息: {message}")

        try:
            msg_data = json.loads(message)
            msg_type = msg_data.get("type")

            if msg_type == "connection_ack":
                logger.info(f"[{self.channel}] 收到连接确认")
                self.is_connection_ack = True
                # 更新连接超时时间
                self.connection_timeout_ms = msg_data.get("connectionTimeoutMs", 300000)
                self.connection_ack_event.set()

            elif msg_type == "ka":
                # 记录最后一次接收keep-alive的时间
                self.last_keepalive_time = time.time()
                logger.debug(f"[{self.channel}] 收到keep-alive消息")

            elif msg_type == "publish_success":
                logger.info(f"[{self.channel}] 消息发布成功: {msg_data}")

            elif msg_type == "publish_error":
                logger.error(f"[{self.channel}] 消息发布失败: {msg_data}")

            elif msg_type == "error":
                logger.error(f"[{self.channel}] 收到错误消息: {msg_data}")

        except Exception as e:
            logger.error(f"[{self.channel}] 处理消息时出错: {e}")

    def on_error(self, ws, error):
        """处理WebSocket错误"""
        logger.error(f"[{self.channel}] WebSocket错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket连接关闭"""
        logger.info(f"[{self.channel}] WebSocket连接关闭: {close_status_code} - {close_msg}")
        self.is_connected = False
        self.is_connection_ack = False

    def on_open(self, ws):
        """处理WebSocket连接打开"""
        logger.info(f"[{self.channel}] WebSocket连接已建立")
        self.is_connected = True
        self.connection_event.set()

        # 发送connection_init消息
        self._send_connection_init()

    def _send_connection_init(self):
        """发送连接初始化消息"""
        try:
            # 根据AWS AppSync文档，connection_init消息非常简单
            init_message = json.dumps({"type": "connection_init"})
            if self.ws is not None:
                self.ws.send(init_message)
                logger.info(f"[{self.channel}] 已发送连接初始化消息")
            else:
                logger.error(f"[{self.channel}] WebSocket连接未初始化，无法发送初始化消息")
        except Exception as e:
            logger.error(f"[{self.channel}] 发送连接初始化消息失败: {e}")

    def connect(self) -> bool:
        """
        建立WebSocket连接

        Returns:
            bool: 是否成功连接并完成初始化
        """
        try:
            logger.info(f"[{self.channel}] 正在连接到AWS AppSync...")
            self.ws = WebSocketApp(
                f"wss://{self.REALTIME_DOMAIN}/event/realtime",
                subprotocols=['aws-appsync-event-ws', self.get_auth_protocol()],
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )

            # 在新线程中运行WebSocket连接
            websocket_thread = threading.Thread(target=self.ws.run_forever)
            websocket_thread.daemon = True
            websocket_thread.start()

            # 等待连接建立，最多等待60秒
            if not self.connection_event.wait(timeout=60):
                logger.error(f"[{self.channel}] 连接超时")
                return False

            # 等待connection_ack, 最多等待30秒
            if not self.connection_ack_event.wait(timeout=30):
                logger.error(f"[{self.channel}] 等待连接确认超时")
                return False

            logger.info(f"[{self.channel}] 连接已完全建立并确认")
            return True

        except Exception as e:
            logger.error(f"[{self.channel}] 连接到AWS AppSync时出错: {e}")
            return False

    def _format_events(self, events: List[AppSyncEvent]) -> List[str]:
        """
        格式化事件为正确的JSON字符串列表

        Args:
            events: 要发布的Pydantic事件模型列表

        Returns:
            List[str]: 格式化后的JSON字符串列表
        """
        formatted_events = []
        for event in events:
            if not isinstance(event, AppSyncEvent):
                raise TypeError(f"事件必须是AppSyncEvent类型，而不是{type(event).__name__}")

            # 确保事件被序列化为JSON字符串
            # AWS AppSync要求events中的每个元素都是JSON字符串
            event_json = event.json()
            formatted_events.append(event_json)

        return formatted_events

    def publish(self, events: List[AppSyncEvent]) -> bool:
        """
        发布事件到AWS AppSync

        Args:
            events: 要发布的Pydantic事件模型列表

        Returns:
            bool: 发布是否成功
        """
        if not self.is_connected:
            logger.error(f"[{self.channel}] 尝试在未连接状态下发布数据")
            return False

        if not self.is_connection_ack:
            logger.error(f"[{self.channel}] 尝试在未收到连接确认的情况下发布数据")
            return False

        if self.ws is None:
            logger.error(f"[{self.channel}] WebSocket连接为空，无法发布数据")
            return False

        try:
            # 格式化事件
            formatted_events = self._format_events(events)

            # 确保API_KEY不为None
            api_key = self.API_KEY
            assert isinstance(api_key, str)

            # 创建消息
            message = AppSyncMessage(
                id=str(uuid.uuid4()),
                type="publish",
                channel=self.channel,
                events=formatted_events,
                authorization=Authorization(**{'x-api-key': api_key})
            )

            # 发送消息
            self.ws.send(message.json(by_alias=True))
            logger.info(f"[{self.channel}] 已发布数据: {formatted_events}")
            return True

        except Exception as e:
            logger.error(f"[{self.channel}] 发布数据时出错: {e}")
            return False

    def close(self) -> None:
        """关闭WebSocket连接"""
        if self.is_connected and self.ws:
            logger.info(f"[{self.channel}] 正在关闭WebSocket连接...")
            self.ws.close()
            self.is_connected = False
            self.is_connection_ack = False
