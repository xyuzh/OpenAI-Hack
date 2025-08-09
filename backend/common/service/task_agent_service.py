from typing import Any, Dict

from common.type.agent import AgentExecuteData, AgentExecuteResult
from common.utils.network_utils import ServerResponseDataFetcher


class SaveTaskAgentResultFetcher(ServerResponseDataFetcher[Any]):
    """保存任务Agent的Fetcher类"""

    def __init__(self, flow_uuid: str, flow_input_uuid: str, task_agent_execute_data: AgentExecuteData):
        """
        初始化更新流程输入类型获取器

        Args:
            flow_input_uuid: 流程输入UUID
        """
        super().__init__("Context Data Fetcher")
        self.flow_uuid = flow_uuid
        self.flow_input_uuid = flow_input_uuid
        self.task_agent_execute_data = task_agent_execute_data

    def get_path(self) -> str:
        """获取API路径"""
        return f"task/agent/internal-api"

    def get_request_config(self) -> Dict[str, Any]:
        """获取请求配置"""
        return {
            'method': 'POST',
            'body': {
                'flow_uuid': self.flow_uuid,
                'flow_input_uuid': self.flow_input_uuid,
                'task_agent_execute_do': self.task_agent_execute_data.model_dump()
            }
        }


async def save_task_agent_result(flow_uuid: str, flow_input_uuid: str,
                                 task_agent_execute_data: AgentExecuteData) -> Any:
    """保存任务Agent"""
    fetcher = SaveTaskAgentResultFetcher(
        flow_uuid, flow_input_uuid, task_agent_execute_data)
    return await fetcher.request()
