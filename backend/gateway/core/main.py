import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.db.redis_pool import initialize_async_redis_pool, close_async_redis_pool
from common.utils.logger_utils import get_logger
from gateway.controller.agent_event_stream_controller import router as agent_event_stream_router
from gateway.controller.health_controller import router as health_router

# Suppress Pydantic serialization warnings from LiteLLM library globally
warnings.filterwarnings("ignore", message=".*PydanticSerializationUnexpectedValue.*Expected.*fields but got.*")

logger = get_logger("gateway.core.main")

# 创建FastAPI应用
app = FastAPI(title="Agent Gateway API", description="提供代理服务的API网关")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router, tags=["Health"])
app.include_router(agent_event_stream_router,
                   prefix="/agent/event-stream", tags=["AgentEventStream"])


# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的事件"""
    logger.info("应用启动")

    # 初始化Redis连接池 - 使用通用的连接池模块
    await initialize_async_redis_pool()


# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的事件"""
    logger.info("应用关闭")

    # 获取全局服务实例并关闭
    try:
        from gateway.controller.agent_event_stream_controller import _event_stream_service
        if _event_stream_service:
            await _event_stream_service.close()
            logger.info("已关闭事件流服务实例")
    except Exception as e:
        logger.error(f"关闭事件流服务时出错: {e}")

    # 关闭Redis连接池 - 使用通用的连接池模块
    await close_async_redis_pool()


if __name__ == "__main__":
    import uvicorn

    logger.info("启动本地服务器")
    # 本地测试
    uvicorn.run(app, host="0.0.0.0", port=8000)