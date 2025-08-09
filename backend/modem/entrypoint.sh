#!/bin/bash

# 确保在项目根目录
cd /app

echo "启动 Celery worker..."
# 如果不是 prod 环境，就用 DEBUG 级别，否则用 INFO
if [ "$ENV" != "prod" ]; then
  # 使用完整模块路径
  celery -A modem.core.main:app worker -l INFO
else
  celery -A modem.core.main:app worker -l INFO
fi