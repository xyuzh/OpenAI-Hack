#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Backend Services...${NC}"
echo "================================="

# Function to check if a service is running
check_service() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✓${NC} Port $1 is already in use (service running)"
        return 0
    else
        echo -e "${YELLOW}✗${NC} Port $1 is free"
        return 1
    fi
}

# Check for required services
echo -e "\n${YELLOW}Checking services...${NC}"

# Check RabbitMQ
if check_service 5672; then
    echo "RabbitMQ appears to be running"
else
    echo -e "${YELLOW}Starting RabbitMQ...${NC}"
    if command -v rabbitmq-server &> /dev/null; then
        rabbitmq-server -detached
        sleep 3
    else
        echo -e "${RED}RabbitMQ not found! Please install it first.${NC}"
        echo "Run: brew install rabbitmq"
        exit 1
    fi
fi

# Check Redis
if check_service 6379; then
    echo "Redis appears to be running"
else
    echo -e "${YELLOW}Starting Redis...${NC}"
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes
        sleep 2
    else
        echo -e "${RED}Redis not found! Please install it first.${NC}"
        echo "Run: brew install redis"
        exit 1
    fi
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.complete to .env and update with your API keys"
    exit 1
fi

# Check for OPENAI_API_KEY in .env
if ! grep -q "^OPENAI_API_KEY=" .env || grep -q "^OPENAI_API_KEY=your_openai_api_key_here" .env; then
    echo -e "${RED}Error: OPENAI_API_KEY not configured in .env!${NC}"
    echo "Please add your OpenAI API key to the .env file"
    exit 1
fi

echo -e "\n${GREEN}Starting Celery Worker...${NC}"
echo "================================="

# Kill existing Celery workers
pkill -f "celery.*modem.core.celery_app.*worker" 2>/dev/null

# Start Celery worker in background
poetry run celery -A modem.core.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --pool=prefork \
    --logfile=celery_worker.log \
    --detach \
    --pidfile=celery_worker.pid

echo "Celery worker started (logs in celery_worker.log)"

echo -e "\n${GREEN}Starting FastAPI Gateway...${NC}"
echo "================================="

# Start FastAPI in the foreground so we can see the logs
echo -e "${YELLOW}Gateway will run in foreground. Press Ctrl+C to stop all services.${NC}"
echo ""

# Trap Ctrl+C to cleanup
trap cleanup INT

cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    # Kill Celery worker
    if [ -f celery_worker.pid ]; then
        kill $(cat celery_worker.pid) 2>/dev/null
        rm celery_worker.pid
    fi
    
    echo -e "${GREEN}Services stopped.${NC}"
    exit 0
}

# Run FastAPI
poetry run uvicorn gateway.core.main:app --reload --host 0.0.0.0 --port 8000