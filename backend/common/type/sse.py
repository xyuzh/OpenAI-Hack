from enum import Enum


class EventStreamSseEvent(str, Enum):
    """SSE事件类型枚举"""
    TASK_AGENT_EXECUTE = "task_agent_execute"  # Agent执行事件
    ERROR = "error"                            # 错误事件
    WAITING = "waiting"                        # 等待事件
    KEEP_ALIVE = "keep_alive"                  # 保活事件
