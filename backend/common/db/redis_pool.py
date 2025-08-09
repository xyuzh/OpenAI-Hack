# -*- coding: utf-8 -*-
"""
Redis连接池管理模块
提供全局Redis连接池的初始化和访问，支持同步和异步操作
"""

from redis import ConnectionPool as SyncConnectionPool
from redis import Redis as SyncRedis
from redis.asyncio import Redis, ConnectionPool

from common.config import Config
from common.utils.logger_utils import get_logger

logger = get_logger("common.db.redis_pool")

# 全局Redis连接池
_async_redis_pool = None
_sync_redis_pool = None


def get_async_redis_pool() -> ConnectionPool | None:
    """
    获取全局异步Redis连接池
    Returns:
        ConnectionPool: 异步Redis连接池实例
    """
    global _async_redis_pool
    return _async_redis_pool


def get_sync_redis_pool():
    """
    获取全局同步Redis连接池
    Returns:
        SyncConnectionPool: 同步Redis连接池实例
    """
    global _sync_redis_pool
    return _sync_redis_pool


async def initialize_async_redis_pool():
    """初始化异步Redis连接池"""
    global _async_redis_pool

    if _async_redis_pool is not None:
        logger.info("异步Redis连接池已存在，跳过初始化")
        return

    # 加载配置
    redis_config = Config.get_redis_config()

    if redis_config is None:
        raise RuntimeError("Redis配置未找到")

    # 创建连接池
    _async_redis_pool = ConnectionPool(
        host=redis_config['redis_host'],
        port=redis_config['redis_port'],
        username=redis_config.get('redis_username', None),
        password=redis_config['redis_password'],
        db=redis_config['redis_db'],
        decode_responses=True,
        max_connections=50,  # 最大连接数
        health_check_interval=30,  # 健康检查间隔
        socket_connect_timeout=5,  # 连接超时
        socket_keepalive=True,  # 保持连接
        socket_timeout=10,  # 套接字超时
        retry_on_timeout=True,  # 超时重试
        retry_on_error=[ConnectionError]  # 错误重试
    )
    logger.info("异步Redis连接池已初始化")


def initialize_sync_redis_pool():
    """初始化同步Redis连接池"""
    global _sync_redis_pool

    if _sync_redis_pool is not None:
        logger.info("同步Redis连接池已存在，跳过初始化")
        return

    # 加载配置
    redis_config = Config.get_redis_config()

    if redis_config is None:
        raise RuntimeError("Redis配置未找到")

    # 创建连接池
    _sync_redis_pool = SyncConnectionPool(
        host=redis_config['redis_host'],
        port=redis_config['redis_port'],
        username=redis_config.get('redis_username', None),
        password=redis_config['redis_password'],
        db=redis_config['redis_db'],
        max_connections=50,  # 最大连接数
        health_check_interval=30,  # 健康检查间隔
        socket_connect_timeout=5,  # 连接超时
        socket_keepalive=True,  # 保持连接
        socket_timeout=10,  # 套接字超时
        retry_on_timeout=True,  # 超时重试
    )
    logger.info("同步Redis连接池已初始化")


async def close_async_redis_pool():
    """关闭异步Redis连接池"""
    global _async_redis_pool
    if _async_redis_pool:
        await _async_redis_pool.disconnect()
        _async_redis_pool = None
        logger.info("异步Redis连接池已关闭")


def close_sync_redis_pool():
    """关闭同步Redis连接池"""
    global _sync_redis_pool
    if _sync_redis_pool:
        _sync_redis_pool = None
        logger.info("同步Redis连接池已关闭")


# 提供获取Redis客户端的便捷方法
def get_sync_redis_client():
    """获取同步Redis客户端"""
    pool = get_sync_redis_pool()
    if not pool:
        raise RuntimeError("同步Redis连接池未初始化")
    return SyncRedis(connection_pool=pool)


async def get_async_redis_client() -> Redis:
    """获取异步Redis客户端"""
    pool = get_async_redis_pool()
    if not pool:
        raise RuntimeError("异步Redis连接池未初始化")
    return Redis(connection_pool=pool)
