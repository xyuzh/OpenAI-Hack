import asyncio
import re

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from kombu import Queue, Exchange
from dotenv import load_dotenv

from common.config import Config
from common.db.redis_pool import initialize_sync_redis_pool, close_sync_redis_pool
from common.utils.logger_utils import get_logger
from modem.type import ProcessFlowDataRequest
from workflow.runner.runner import Runner

# Load environment variables from .env file
load_dotenv()


app = Celery('main')

# Get configuration
celery_config = Config.get_celery_config()

# Extract queue_arguments before removing from config
queue_arguments = celery_config.get('queue_arguments', {})

# Remove queue_arguments from config as it's not a valid Celery config key
if 'queue_arguments' in celery_config:
    celery_config.pop('queue_arguments')

# Update Celery configuration
app.conf.update(celery_config)

# Set up queue with Kombu objects after configuration
queue_name = celery_config.get('task_default_queue', 'celery')
exchange_name = celery_config.get('task_default_exchange', 'celery')
routing_key = celery_config.get('task_default_routing_key', 'celery')

# Create the Queue object and set it directly with queue arguments
app.conf.task_queues = [
    Queue(
        queue_name,
        Exchange(exchange_name, type='direct', durable=True),
        routing_key=routing_key,
        durable=True,
        queue_arguments=queue_arguments  # Pass the queue arguments
    )
]

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
