import base64
import json
import threading
import time
import re
import uuid
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass

from websocket import WebSocketApp
from common.config.config import Config
from common.utils.logger_utils import get_logger
from modem.type.flow_type import Authorization

logger = get_logger("modem.dev.app_sync_demo")


@dataclass
class ReceivedMessage:
    """接收到的消息结构"""
    timestamp: float
    message_type: str
    data: Dict[str, Any]
    raw_message: str


class AppSyncReceiveMessageService:
    """AppSync消息接收服务"""

    def __init__(self, http_domain: str, websocket_domain: str, api_key: str,
                 user_uuid: str, message_callback: Optional[Callable] = None):
        # 验证必要参数
        if not all([http_domain, websocket_domain, api_key, user_uuid]):
            raise ValueError("AppSyncReceiveMessageService初始化失败: 所有参数都不能为空")

        # AppSync配置
        self.HTTP_DOMAIN = http_domain
        self.REALTIME_DOMAIN = websocket_domain
        self.API_KEY = api_key
        self.user_uuid = user_uuid

        # 创建唯一channel
        self.channel = f"celery-agent-event/{self._remove_non_alphanumeric(user_uuid)}"

        # WebSocket连接相关
        self.ws = None
        self.is_connected = False
        self.is_connection_ack = False
        self.connection_event = threading.Event()
        self.connection_ack_event = threading.Event()

        # 订阅相关
        self.subscriptions: Dict[str, str] = {}  # subscription_id -> channel
        self.is_subscribed = False

        # 连接超时和心跳检测
        self.connection_timeout_ms = 300000  # 默认值，会从connection_ack更新
        self.last_keepalive_time = None

        # 消息处理相关
        self.messages: List[ReceivedMessage] = []
        self.last_processed_index = 0
        self.message_lock = threading.Lock()
        self.message_callback = message_callback

        # 消息处理循环相关
        self.is_processing = False
        self.processing_thread = None

    def _remove_non_alphanumeric(self, text: str) -> str:
        """移除非字母数字字符"""
        return re.sub(r'[^a-zA-Z0-9]', '', text)

    def get_auth_protocol(self) -> str:
        """生成WebSocket连接的认证协议"""
        authorization = Authorization(
            **{'x-api-key': self.API_KEY, 'host': self.HTTP_DOMAIN}
        )

        header_json = authorization.json(by_alias=True)
        header_bytes = header_json.encode('utf-8')
        header_base64 = base64.b64encode(header_bytes).decode('utf-8')
        header_encoded = header_base64.replace(
            '+', '-').replace('/', '_').rstrip('=')
        return f"header-{header_encoded}"

    def add_message(self, message_type: str, data: Dict[str, Any], raw_message: str):
        """添加新消息（线程安全）"""
        with self.message_lock:
            received_msg = ReceivedMessage(
                timestamp=time.time(),
                message_type=message_type,
                data=data,
                raw_message=raw_message
            )
            self.messages.append(received_msg)

            # 如果有回调函数，调用它
            if self.message_callback:
                try:
                    self.message_callback(received_msg)
                except Exception as e:
                    logger.error(f"[{self.channel}] 执行消息回调时出错: {e}")

    def get_new_messages(self) -> List[ReceivedMessage]:
        """获取自上次处理以来的新消息（线程安全）"""
        with self.message_lock:
            new_messages = self.messages[self.last_processed_index:]
            self.last_processed_index = len(self.messages)
            return new_messages.copy()

    def has_new_messages(self) -> bool:
        """检查是否有新消息"""
        with self.message_lock:
            return len(self.messages) > self.last_processed_index

    def get_message_count(self) -> int:
        """获取总消息数量"""
        with self.message_lock:
            return len(self.messages)

    def _send_message(self, message: Dict[str, Any]):
        """发送WebSocket消息"""
        if self.ws and self.is_connected:
            try:
                self.ws.send(json.dumps(message))
                logger.debug(f"[{self.channel}] 发送消息: {message}")
            except Exception as e:
                logger.error(f"[{self.channel}] 发送消息失败: {e}")
        else:
            logger.error(f"[{self.channel}] WebSocket未连接，无法发送消息")

    def subscribe_to_channel(self) -> str:
        """订阅频道"""
        if not self.is_connection_ack:
            logger.error(f"[{self.channel}] 连接未确认，无法订阅频道")
            return ""

        # 生成唯一订阅ID
        subscription_id = f"sub-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
        
        # 创建授权对象
        authorization = {
            'x-api-key': self.API_KEY,
            'host': self.HTTP_DOMAIN
        }

        # 创建订阅消息
        subscribe_msg = {
            "type": "subscribe",
            "id": subscription_id,
            "channel": self.channel,
            "authorization": authorization
        }

        # 发送订阅消息
        self._send_message(subscribe_msg)
        
        # 保存订阅信息
        self.subscriptions[subscription_id] = self.channel
        
        logger.info(f"[{self.channel}] 发送订阅请求，ID: {subscription_id}")
        return subscription_id

    def on_message(self, ws, message):
        """处理接收到的WebSocket消息"""
        logger.info(f"[{self.channel}] 收到消息: {message}")

        try:
            msg_data = json.loads(message)
            msg_type = msg_data.get("type")

            # 将所有消息都添加到消息列表
            self.add_message(msg_type, msg_data, message)

            # 处理特殊类型的消息
            if msg_type == "connection_ack":
                logger.info(f"[{self.channel}] 收到连接确认")
                self.is_connection_ack = True
                # 更新连接超时时间
                self.connection_timeout_ms = msg_data.get("connectionTimeoutMs", 300000)
                self.connection_ack_event.set()
                
                # 连接确认后自动订阅频道
                self.subscribe_to_channel()

            elif msg_type == "ka":
                # 记录最后一次接收keep-alive的时间
                self.last_keepalive_time = time.time()
                logger.debug(f"[{self.channel}] 收到keep-alive消息")

            elif msg_type == "subscribe_success":
                # 订阅成功
                subscription_id = msg_data.get("id")
                logger.info(f"[{self.channel}] 订阅成功，ID: {subscription_id}")
                self.is_subscribed = True

            elif msg_type == "subscribe_error":
                # 订阅错误
                subscription_id = msg_data.get("id")
                errors = msg_data.get("errors", [])
                logger.error(f"[{self.channel}] 订阅失败，ID: {subscription_id}, 错误: {errors}")

            elif msg_type == "data":
                # 接收到频道数据 - 这是实际的业务消息
                logger.info(f"[{self.channel}] 接收到频道数据: {msg_data}")

            elif msg_type == "error":
                logger.error(f"[{self.channel}] 收到错误消息: {msg_data}")

        except Exception as e:
            logger.error(f"[{self.channel}] 处理消息时出错: {e}")
            # 即使解析失败，也保存原始消息
            self.add_message("parse_error", {"error": str(e)}, message)

    def on_error(self, ws, error):
        """处理WebSocket错误"""
        logger.error(f"[{self.channel}] WebSocket错误: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket连接关闭"""
        logger.info(
            f"[{self.channel}] WebSocket连接关闭: {close_status_code} - {close_msg}")
        self.is_connected = False
        self.is_connection_ack = False
        self.is_subscribed = False

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
            init_message = {"type": "connection_init"}
            self._send_message(init_message)
            logger.info(f"[{self.channel}] 已发送连接初始化消息")
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

    def start_message_processing(self):
        """启动消息处理循环"""
        if self.is_processing:
            logger.warning(f"[{self.channel}] 消息处理已在运行中")
            return

        self.is_processing = True
        self.processing_thread = threading.Thread(
            target=self._message_processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info(f"[{self.channel}] 消息处理循环已启动")

    def _message_processing_loop(self):
        """消息处理循环（在单独线程中运行）"""
        while self.is_processing:
            try:
                if self.has_new_messages():
                    new_messages = self.get_new_messages()

                    if new_messages:
                        logger.info(
                            f"[{self.channel}] 处理 {len(new_messages)} 条新消息")

                        for i, msg in enumerate(new_messages):
                            self._process_single_message(msg, i + 1)

                # 等待一段时间再检查
                time.sleep(1)  # 每秒检查一次

            except Exception as e:
                logger.error(f"[{self.channel}] 消息处理循环出错: {e}")
                time.sleep(5)  # 出错后等待5秒再继续

    def _process_single_message(self, message: ReceivedMessage, sequence: int):
        """处理单条消息 - 在这里添加你的业务逻辑"""
        logger.info(
            f"[{self.channel}] [{sequence}] 处理消息类型: {message.message_type}")

        # 根据消息类型执行不同的业务逻辑
        if message.message_type == "connection_ack":
            self._handle_connection_ack(message)
        elif message.message_type == "ka":
            self._handle_keepalive(message)
        elif message.message_type == "subscribe_success":
            self._handle_subscribe_success(message)
        elif message.message_type == "subscribe_error":
            self._handle_subscribe_error(message)
        elif message.message_type == "data":
            self._handle_data_message(message)
        elif message.message_type == "error":
            self._handle_error(message)
        elif message.message_type == "parse_error":
            self._handle_parse_error(message)
        else:
            self._handle_unknown_message(message)

    def _handle_connection_ack(self, message: ReceivedMessage):
        """处理连接确认消息"""
        timeout_ms = message.data.get("connectionTimeoutMs", 300000)
        logger.info(f"[{self.channel}] 连接已确认，超时时间: {timeout_ms}ms")

    def _handle_keepalive(self, message: ReceivedMessage):
        """处理心跳消息"""
        logger.debug(f"[{self.channel}] 心跳正常")

    def _handle_subscribe_success(self, message: ReceivedMessage):
        """处理订阅成功消息"""
        subscription_id = message.data.get("id")
        logger.info(f"[{self.channel}] 频道订阅成功，ID: {subscription_id}")

    def _handle_subscribe_error(self, message: ReceivedMessage):
        """处理订阅错误消息"""
        subscription_id = message.data.get("id")
        errors = message.data.get("errors", [])
        logger.error(f"[{self.channel}] 频道订阅失败，ID: {subscription_id}")
        for error in errors:
            logger.error(f"[{self.channel}] 订阅错误详情: {error}")

    def _handle_data_message(self, message: ReceivedMessage):
        """处理数据消息 - 这是实际的业务数据"""
        logger.info(f"[{self.channel}] 接收到业务数据: {message.data}")
        
        # 提取事件数据
        events = message.data.get("event", [])
        if isinstance(events, str):
            try:
                # 如果event是字符串，尝试解析为JSON
                event_data = json.loads(events)
                logger.info(f"[{self.channel}] 解析后的事件数据: {event_data}")
                # TODO: 在这里添加你的具体业务处理逻辑
                self._process_business_event(event_data)
            except json.JSONDecodeError as e:
                logger.error(f"[{self.channel}] 解析事件数据失败: {e}")
        elif isinstance(events, list):
            # 如果event是列表，逐个处理
            for event in events:
                if isinstance(event, str):
                    try:
                        event_data = json.loads(event)
                        logger.info(f"[{self.channel}] 解析后的事件数据: {event_data}")
                        self._process_business_event(event_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"[{self.channel}] 解析事件数据失败: {e}")
                else:
                    logger.info(f"[{self.channel}] 直接处理事件数据: {event}")
                    self._process_business_event(event)

    def _process_business_event(self, event_data: Any):
        """处理具体的业务事件 - 在这里添加你的业务逻辑"""
        logger.info(f"[{self.channel}] 处理业务事件: {event_data}")
        # TODO: 根据event_data的内容实现你的业务逻辑
        # 例如：
        # - 任务状态更新
        # - 用户通知
        # - 系统事件
        # etc.

    def _handle_error(self, message: ReceivedMessage):
        """处理错误消息"""
        logger.error(f"[{self.channel}] 收到错误: {message.data}")

    def _handle_parse_error(self, message: ReceivedMessage):
        """处理解析错误"""
        error = message.data.get("error", "未知解析错误")
        logger.error(f"[{self.channel}] 消息解析失败: {error}")
        logger.error(f"[{self.channel}] 原始消息: {message.raw_message}")

    def _handle_unknown_message(self, message: ReceivedMessage):
        """处理未知类型消息"""
        logger.warning(f"[{self.channel}] 未知消息类型: {message.message_type}")
        logger.debug(f"[{self.channel}] 消息内容: {message.data}")

    def start(self) -> bool:
        """启动服务：连接并开始消息处理"""
        try:
            # 连接
            if not self.connect():
                logger.error(f"[{self.channel}] AppSync连接失败")
                return False

            # 启动消息处理循环
            self.start_message_processing()

            logger.info(
                f"[{self.channel}] AppSync消息接收服务已启动，user: {self.user_uuid}")
            return True

        except Exception as e:
            logger.error(f"[{self.channel}] 启动AppSync消息接收服务失败: {e}")
            return False

    def close(self) -> None:
        """关闭WebSocket连接和停止消息处理"""
        logger.info(f"[{self.channel}] 正在停止AppSync消息接收服务...")

        # 停止消息处理
        self.is_processing = False

        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)

        # 取消所有订阅
        for subscription_id in list(self.subscriptions.keys()):
            try:
                unsubscribe_msg = {
                    "type": "unsubscribe",
                    "id": subscription_id
                }
                self._send_message(unsubscribe_msg)
                logger.info(f"[{self.channel}] 取消订阅: {subscription_id}")
            except Exception as e:
                logger.error(f"[{self.channel}] 取消订阅时出错: {e}")

        self.subscriptions.clear()

        # 关闭WebSocket连接
        if self.is_connected and self.ws:
            logger.info(f"[{self.channel}] 正在关闭WebSocket连接...")
            self.ws.close()
            self.is_connected = False
            self.is_connection_ack = False
            self.is_subscribed = False

        logger.info(f"[{self.channel}] AppSync消息接收服务已停止")

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "user_uuid": self.user_uuid,
            "channel": self.channel,
            "is_connected": self.is_connected,
            "is_connection_ack": self.is_connection_ack,
            "is_subscribed": self.is_subscribed,
            "is_processing": self.is_processing,
            "total_messages": self.get_message_count(),
            "has_new_messages": self.has_new_messages(),
            "subscriptions": list(self.subscriptions.keys()),
            "last_keepalive_time": self.last_keepalive_time,
            "connection_timeout_ms": self.connection_timeout_ms
        }


# 使用示例
def main():
    """主函数演示如何使用AppSyncReceiveMessageService"""

    print("=== AppSync Receive Message Service Demo ===")

    appsync_config = Config.get_aws_app_sync_config()

    user_uuid = "1234567890"

    def on_message_callback(message: ReceivedMessage):
        """消息接收回调示例"""
        print(
            f"回调收到消息: {message.message_type} at {time.strftime('%H:%M:%S', time.localtime(message.timestamp))}")

    try:
        # 创建服务实例
        service = AppSyncReceiveMessageService(
            http_domain=appsync_config["http_domain"],
            websocket_domain=appsync_config["websocket_domain"],
            api_key=appsync_config["api_key"],
            user_uuid=user_uuid,
            message_callback=on_message_callback
        )

        # 启动服务
        if not service.start():
            print("服务启动失败")
            return

        # 主循环 - 模拟其他业务逻辑
        print("服务已启动，进入主业务循环...")
        print("(按 Ctrl+C 退出)")

        counter = 0
        while True:
            # 模拟主业务逻辑
            time.sleep(10)

            counter += 1
            print(f"\n--- 主业务循环 #{counter} ({time.strftime('%H:%M:%S')}) ---")

            # 检查状态
            status = service.get_status()
            print(f"用户: {status['user_uuid']}")
            print(f"Channel: {status['channel']}")
            print(f"连接状态: {'✓' if status['is_connected'] else '✗'}")
            print(f"认证状态: {'✓' if status['is_connection_ack'] else '✗'}")
            print(f"订阅状态: {'✓' if status['is_subscribed'] else '✗'}")
            print(f"处理状态: {'运行中' if status['is_processing'] else '已停止'}")
            print(f"消息总数: {status['total_messages']}")
            print(f"有新消息: {'是' if status['has_new_messages'] else '否'}")
            print(f"活跃订阅: {len(status['subscriptions'])}")

    except KeyboardInterrupt:
        print("\n收到中断信号，正在退出...")
    except Exception as e:
        print(f"\n程序出错: {e}")
    finally:
        if 'service' in locals():
            service.close()
        print("程序已结束")


if __name__ == "__main__":
    main()