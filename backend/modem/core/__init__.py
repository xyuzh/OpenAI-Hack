"""
Modem核心处理模块

提供Celery任务和流数据处理功能。
作为Modem包的一部分，负责处理所有与流数据相关的操作。
"""

# 从main模块导入所有必要的组件
from .main import app, process_flow_data, remove_non_alphanumeric

# 定义导出的符号
__all__ = ['app', 'process_flow_data', 'remove_non_alphanumeric']

# 包版本
__version__ = '1.0.0'
