#!/bin/bash

# 确保在项目根目录
cd /app

echo "启动 FastAPI worker..."
# 如果不是 prod 环境，就用 DEBUG 级别，否则用 INFO
if [ "$ENV" != "prod" ]; then
  # 使用完整模块路径
  uvicorn gateway.core.main:app --reload --log-level info --access-log --host 0.0.0.0 --port 8080
else
  uvicorn gateway.core.main:app --reload --log-level info --access-log --host 0.0.0.0 --port 8080
fi