"""
Modem配置模块

提供配置加载和管理功能，基于环境变量和配置文件。
作为Modem包的一部分，负责处理所有与配置相关的操作。
"""

# 导入Config类，作为主要配置接口
from .config import Config

# 定义导出的符号
__all__ = ['Config']
