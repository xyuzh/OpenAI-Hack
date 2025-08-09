from enum import Enum


class CurrentState(str, Enum):
    """
    初始化
    """
    INIT = "init"

    """
    处理中
    """
    PROCESSING = "processing"

    """
    中断
    """
    INTERRUPT = "interrupt"

    """
    完成
    """
    COMPLETE = "complete"

    """
    错误
    """
    ERROR = "error"
