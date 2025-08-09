from typing import Generic, TypeVar, Optional, Dict, Any

import httpx
from pydantic import BaseModel

from common.config import Config

# 定义泛型类型变量
T = TypeVar('T')


# 基于Java中的ServerResponseBase创建Pydantic模型
class ServerResponseBase(BaseModel):
    code: int
    message: Optional[str] = None


# 基于Java中的ServerResponse创建Pydantic模型
class ServerResponse(ServerResponseBase, Generic[T]):
    data: Optional[T] = None


class ServerResponseDataFetcher(Generic[T]):
    """
    服务器响应数据获取器基类，参考自Next.js实现
    负责封装HTTP请求的细节，提供统一的接口
    """

    def __init__(self, log_prefix: str):
        """
        初始化数据获取器

        Args:
            log_prefix: 日志前缀，用于标识日志来源
        """
        self.log_prefix = log_prefix

    def get_path(self) -> str:
        """
        获取API路径
        子类必须实现此方法
        """
        raise NotImplementedError("Subclasses must implement get_path()")

    def get_request_config(self) -> Dict[str, Any]:
        """
        获取请求配置
        子类必须实现此方法

        返回值应包含:
            - method: HTTP方法 (GET, POST等)
            - search_params: URL查询参数 (可选)
            - body: 请求体数据 (可选)
        """
        raise NotImplementedError("Subclasses must implement get_request_config()")

    def get_server_host(self) -> str:
        """获取服务器主机地址"""
        usebase_server_boot_config = Config.get_usebase_server_boot_config()
        return usebase_server_boot_config['usebase_server_boot_base_url']

    def _build_url(self) -> str:
        """构建完整的URL"""
        config = self.get_request_config()
        path = self.get_path()

        # 处理查询参数
        if 'search_params' in config and config['search_params']:
            params = config['search_params']
            # 构建查询字符串
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={value}")

            if query_parts:
                path += f"?{'&'.join(query_parts)}"

        return f"{self.get_server_host()}/{path}"

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        usebase_server_boot_config = Config.get_usebase_server_boot_config()
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': usebase_server_boot_config['usebase_internal_api_key'],
        }

        return headers

    async def request(self) -> T:
        """
        执行请求并返回处理后的数据

        Returns:
            解析后的响应数据

        Raises:
            Exception: 当请求失败或解析失败时
        """
        config = self.get_request_config()
        method = config.get('method')
        url = self._build_url()
        headers = self._build_headers()

        # 准备请求参数
        request_kwargs = {
            'headers': headers,
            'timeout': 30.0
        }

        # 添加请求体（如果存在）
        if 'body' in config and config['body'] and method.upper() in ['POST', 'PUT', 'PATCH']:
            request_kwargs['json'] = config['body']

        # 使用httpx发送请求
        async with httpx.AsyncClient() as client:
            if method.upper() == 'GET':
                response = await client.get(url, **request_kwargs)
            elif method.upper() == 'POST':
                response = await client.post(url, **request_kwargs)
            elif method.upper() == 'PUT':
                response = await client.put(url, **request_kwargs)
            elif method.upper() == 'DELETE':
                response = await client.delete(url, **request_kwargs)
            elif method.upper() == 'PATCH':
                response = await client.patch(url, **request_kwargs)
            elif method.upper() == 'OPTIONS':
                response = await client.options(url, **request_kwargs)
            elif method.upper() == 'HEAD':
                response = await client.head(url, **request_kwargs)
            elif method.upper() == 'TRACE':
                response = await client.trace(url, **request_kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # 解析响应
            response_json = response.json()
            server_response = ServerResponse[T].parse_obj(response_json)

            # 检查业务逻辑代码
            if server_response.code != 200:
                error_msg = server_response.message or f"Error code: {server_response.code}"
                raise Exception(f"Network Request Error: {error_msg}")

            # 返回数据部分（不再包含ServerResponse包装）
            return server_response.data
