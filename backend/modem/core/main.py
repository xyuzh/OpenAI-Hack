import asyncio
import re

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from common.config import Config
from common.db.redis_pool import initialize_sync_redis_pool, close_sync_redis_pool
from common.utils.logger_utils import get_logger
from modem.type import ProcessFlowDataRequest
from workflow.runner.runner import Runner


app = Celery('main')

app.conf.update(Config.get_celery_config())

logger = get_logger("modem.core.main")


@worker_process_init.connect
def worker_init_handler(**kwargs):
    """Initialize each Celery worker process"""
    initialize_sync_redis_pool()
    logger.info(f"Celery worker version {Config.get_app_config()['app_version']} initialized")


@worker_process_shutdown.connect
def worker_shutdown_handler(**kwargs):
    """Clean up when worker shuts down"""
    close_sync_redis_pool()
    logger.info("Celery worker shutdown completed")


def remove_non_alphanumeric(string):
    """
    移除字符串中所有非字母和数字的字符

    Args:
        string: 需要处理的字符串

    Returns:
        只包含字母和数字的字符串
    """
    # 使用正则表达式匹配所有非字母和数字的字符，并替换为空字符串
    return re.sub(r'[^a-zA-Z0-9]', '', string)


@app.task(name='main.process_flow_data')
def process_flow_data(data):
    """
    处理流数据的任务

    Args:
        data: 包含ProcessFlowDataRequest的JSON字符串

    Returns:
        处理结果
    """
    logger.info(f"Received data: {data}")

    # 解析请求数据
    request = ProcessFlowDataRequest.from_json(data)
    logger.info(
        f"Processing flow data with flow_input_uuid: {request.flow_input_uuid}")

    Runner.run_flow(request)
