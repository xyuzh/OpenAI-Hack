import json
from enum import Enum
from typing import List, Any, Optional, TypeVar, Generic

from pydantic import BaseModel, Field


class Authorization(BaseModel):
    """授权信息模型"""
    x_api_key: str = Field(alias='x-api-key')
    host: Optional[str] = None


class AppSyncMessage(BaseModel):
    """AppSync消息模型"""
    id: str
    type: str
    channel: str
    events: List[str]
    authorization: Authorization


class AppSyncEventType(Enum):
    """AppSync事件类型枚举"""
    flow_input_type_determine = "flow_input_type_determine"


T = TypeVar('T')


class AppSyncEvent(BaseModel, Generic[T]):
    """AppSync事件模型基类 - 所有事件都应继承此类"""
    event_type: AppSyncEventType
    data: T

    class Config:
        arbitrary_types_allowed = True


class ProcessFlowDataRequest(BaseModel):
    """
    Celery流程数据处理请求

    用于从Java服务接收处理流程数据的任务请求参数
    """
    flow_uuid: str
    flow_input_uuid: str
    user_uuid: str
    context_data: List[dict]

    @classmethod
    def from_json(cls, json_str: str) -> 'ProcessFlowDataRequest':
        """
        从JSON字符串创建ProcessFlowDataRequest对象

        Args:
            json_str: JSON字符串

        Returns:
            ProcessFlowDataRequest对象
        """
        data = json.loads(json_str)
        return cls(**data)
