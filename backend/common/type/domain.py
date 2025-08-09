from enum import Enum


class DomainType(str, Enum):
    """领域类型"""
    # 流程
    FLOW = "flow"
    # 任务输入
    FLOW_INPUT = "flow_input"
    # 任务Agent执行
    TASK_AGENT_EXECUTE = "task_agent_execute"


__all__ = ["DomainType"]
