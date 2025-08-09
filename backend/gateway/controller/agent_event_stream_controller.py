from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from starlette.responses import StreamingResponse

from common.utils.logger_utils import get_logger
from gateway.service.agent_event_stream_service import (
    AgentEventStreamService,
    StreamConnectionException,
    StreamTimeoutException,
    StreamRedisException,
    StreamClientDisconnectedException
)

# 创建路由器
router = APIRouter()

logger = get_logger("gateway.controller.agent_event_stream_controller")

# 全局服务实例
_event_stream_service = None


async def get_event_stream_service():
    """
    获取全局事件流服务实例
    应用级单例模式，确保整个应用只创建一个服务实例

    Raises:
        HTTPException: 当服务初始化失败时
    """
    global _event_stream_service
    if _event_stream_service is None:
        logger.info("创建全局事件流服务实例")
        try:
            _event_stream_service = AgentEventStreamService()
            await _event_stream_service.initialize()
            logger.info("事件流服务实例创建成功")
        except StreamRedisException as e:
            logger.error(f"事件流服务初始化失败，Redis连接异常: {e}")
            raise HTTPException(status_code=503, detail=f"服务不可用，Redis连接失败: {str(e)}")
        except Exception as e:
            logger.error(f"事件流服务初始化失败，未知异常: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"服务初始化失败: {str(e)}")

    return _event_stream_service


def _get_http_status_for_exception(exception: Exception) -> int:
    """
    根据异常类型确定HTTP状态码

    Args:
        exception: 捕获的异常

    Returns:
        int: 对应的HTTP状态码
    """
    if isinstance(exception, StreamTimeoutException):
        return 408  # Request Timeout
    elif isinstance(exception, StreamRedisException):
        return 503  # Service Unavailable
    elif isinstance(exception, StreamClientDisconnectedException):
        return 499  # Client Closed Request (Nginx标准，表示客户端主动断开)
    elif isinstance(exception, StreamConnectionException):
        return 500  # Internal Server Error
    else:
        return 500  # Internal Server Error


def _get_error_message_for_exception(exception: Exception) -> str:
    """
    根据异常类型生成用户友好的错误信息

    Args:
        exception: 捕获的异常

    Returns:
        str: 用户友好的错误信息
    """
    if isinstance(exception, StreamTimeoutException):
        return "请求超时，可能因为：流程创建时间过长、长时间无业务数据更新或连接存活时间过长"
    elif isinstance(exception, StreamRedisException):
        return "服务暂时不可用，请稍后重试"
    elif isinstance(exception, StreamClientDisconnectedException):
        return "客户端连接已断开"
    elif isinstance(exception, StreamConnectionException):
        return "连接异常，请检查网络状态"
    else:
        return "服务器内部错误"


@router.get("")
async def stream_llm_content(
        request: Request,
        flowUuid: str,
        flowInputUuid: str,
        last_id: Optional[str] = None,
        service: AgentEventStreamService = Depends(get_event_stream_service)
):
    """
    SSE端点: 获取LLM流式响应

    注意：现在使用双重超时机制：
    1. 业务消息超时：当超过配置时间没有收到业务消息时触发
    2. 连接绝对超时：连接存活超过最大允许时间时触发

    Args:
        request: FastAPI请求对象
        flowUuid: 流程UUID
        flowInputUuid: 流程输入UUID
        last_id: 上次读取的消息ID (可选，用于断点续传)
        service: 事件流服务实例 (依赖注入)

    Returns:
        StreamingResponse: SSE流式响应

    Raises:
        HTTPException: 各种服务异常对应的HTTP错误
    """
    logger.info(
        f"客户端请求建立SSE连接 - flowUuid={flowUuid}, flowInputUuid={flowInputUuid}, last_id={last_id}, "
        f"client_host={request.client.host if request.client else 'unknown'}"
    )

    try:
        # 参数验证
        if not flowUuid or not flowUuid.strip():
            logger.warning(f"无效的flowUuid参数: '{flowUuid}'")
            raise HTTPException(status_code=400, detail="flowUuid参数不能为空")

        if not flowInputUuid or not flowInputUuid.strip():
            logger.warning(f"无效的flowInputUuid参数: '{flowInputUuid}'")
            raise HTTPException(status_code=400, detail="flowInputUuid参数不能为空")

        # 创建SSE响应流
        event_stream = service.stream_sse_events(
            request=request,
            flow_uuid=flowUuid.strip(),
            flow_input_uuid=flowInputUuid.strip(),
            last_id=last_id.strip() if last_id else None
        )

        logger.info(f"SSE连接建立成功: {flowUuid}.{flowInputUuid}")

        # 返回流式响应
        response = StreamingResponse(
            content=event_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用Nginx缓冲，确保实时性
                "Access-Control-Allow-Origin": "*",  # 允许跨域访问
                "Access-Control-Allow-Headers": "Cache-Control"
            },
        )

        return response

    except StreamClientDisconnectedException as e:
        # 客户端断开连接是正常情况，记录info级别日志
        logger.info(f"客户端主动断开SSE连接: {flowUuid}.{flowInputUuid} - {str(e)}")
        # 客户端断开连接时，返回特殊状态码但不抛出HTTPException
        # 因为连接已经断开，客户端不会收到响应
        raise HTTPException(
            status_code=_get_http_status_for_exception(e),
            detail=_get_error_message_for_exception(e)
        )

    except StreamTimeoutException as e:
        # 超时异常 - 包括Stream创建等待超时、业务消息超时和连接绝对超时
        logger.warning(f"SSE连接超时: {flowUuid}.{flowInputUuid} - {str(e)}")
        raise HTTPException(
            status_code=_get_http_status_for_exception(e),
            detail=_get_error_message_for_exception(e)
        )

    except StreamRedisException as e:
        # Redis连接异常，记录error级别日志
        logger.error(f"SSE连接Redis异常: {flowUuid}.{flowInputUuid} - {str(e)}")
        raise HTTPException(
            status_code=_get_http_status_for_exception(e),
            detail=_get_error_message_for_exception(e)
        )

    except StreamConnectionException as e:
        # 其他连接异常，记录error级别日志
        logger.error(f"SSE连接异常: {flowUuid}.{flowInputUuid} - {str(e)}")
        raise HTTPException(
            status_code=_get_http_status_for_exception(e),
            detail=_get_error_message_for_exception(e)
        )

    except ValueError as e:
        # 参数验证异常
        logger.warning(f"SSE请求参数错误: {flowUuid}.{flowInputUuid} - {str(e)}")
        raise HTTPException(status_code=400, detail=f"请求参数错误: {str(e)}")

    except Exception as e:
        # 捕获所有其他未预期的异常
        error_msg = f"SSE服务发生未预期异常: {str(e)}"
        logger.error(f"{error_msg} - flowUuid={flowUuid}, flowInputUuid={flowInputUuid}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="服务器内部错误，请稍后重试"
        )

    finally:
        # 记录连接结束日志
        logger.debug(f"SSE连接处理结束: {flowUuid}.{flowInputUuid}")