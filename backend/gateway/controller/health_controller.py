# -*- coding: utf-8 -*-
"""
健康检查控制器
提供健康状态检查端点
"""
from datetime import datetime, timezone

from fastapi import APIRouter

from common.config import Config
from common.utils.logger_utils import get_logger

# 创建路由器
router = APIRouter()

logger = get_logger("gateway.controller.health_controller")


@router.get("/health")
async def health_check():
    """
    健康检查端点

    Returns:
        dict: 包含健康状态的字典
    """
    # 获取配置健康状态
    logger.debug("执行健康检查")
    config_status = Config.get_health_status()

    # 构建健康检查响应
    health_response = {
        "status": config_status["overall_status"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config_status": config_status
    }

    return health_response
