#!/bin/bash
set -e

echo "�� 启动 Modem 服务..."

# 设置环境变量
export ENV=local

# 显示 Python 版本
echo "检查 Python 版本:"
poetry run python -c "import sys; print(f'Python 版本: {sys.version}')"
poetry run python -c "import sys; print(f'Python 路径: {sys.executable}')"

# 显示启动信息
echo "====================================="
echo "  启动 Celery Worker (ENV=local)"
echo "====================================="

# 使用 poetry run 确保在正确的虚拟环境中执行
poetry run celery -A modem.core.main:app worker -l INFO
