#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Backend Services Startup Guide${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check if a service is running
check_service() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Port $1 is in use (service likely running)"
        return 0
    else
        echo -e "${YELLOW}✗${NC} Port $1 is free"
        return 1
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "\n${BLUE}Step 1: Checking Prerequisites${NC}"
echo "--------------------------------"

# Check for required commands
MISSING_DEPS=()

if ! command_exists rabbitmq-server; then
    MISSING_DEPS+=("rabbitmq")
fi

if ! command_exists redis-server; then
    MISSING_DEPS+=("redis")
fi

if ! command_exists poetry; then
    MISSING_DEPS+=("poetry")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}Missing required dependencies:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo -e "  ${YELLOW}• $dep${NC}"
    done
    echo -e "\n${YELLOW}Install with Homebrew:${NC}"
    echo "  brew install ${MISSING_DEPS[*]}"
    exit 1
fi

echo -e "${GREEN}✓${NC} All required commands found"

# Check if .env file exists
echo -e "\n${BLUE}Step 2: Checking Configuration${NC}"
echo "--------------------------------"

if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found!${NC}"
    echo -e "${YELLOW}Please copy .env.complete to .env and update with your API keys:${NC}"
    echo "  cp .env.complete .env"
    echo "  # Then edit .env to add your OPENAI_API_KEY and COMPOSIO_API_KEY"
    exit 1
fi

# Check for required API keys
if ! grep -q "^OPENAI_API_KEY=" .env || grep -q "^OPENAI_API_KEY=your_openai_api_key_here" .env; then
    echo -e "${YELLOW}⚠ OPENAI_API_KEY not configured in .env${NC}"
    echo "Please add your OpenAI API key to the .env file"
fi

if ! grep -q "^COMPOSIO_API_KEY=" .env || grep -q "^COMPOSIO_API_KEY=your_composio_api_key_here" .env; then
    echo -e "${YELLOW}⚠ COMPOSIO_API_KEY not configured in .env${NC}"
    echo "Please add your Composio API key to the .env file"
fi

echo -e "${GREEN}✓${NC} Configuration file found"

# Check RabbitMQ
echo -e "\n${BLUE}Step 3: Checking RabbitMQ${NC}"
echo "--------------------------------"

if check_service 5672; then
    echo -e "${GREEN}✓${NC} RabbitMQ appears to be running"
else
    echo -e "${YELLOW}RabbitMQ is not running.${NC}"
    echo -e "Start it with: ${GREEN}rabbitmq-server${NC}"
    echo -e "Or in background: ${GREEN}brew services start rabbitmq${NC}"
fi

# Check Redis
echo -e "\n${BLUE}Step 4: Checking Redis${NC}"
echo "--------------------------------"

if check_service 6379; then
    echo -e "${GREEN}✓${NC} Redis appears to be running"
else
    echo -e "${YELLOW}Redis is not running.${NC}"
    echo -e "Start it with: ${GREEN}redis-server${NC}"
    echo -e "Or in background: ${GREEN}brew services start redis${NC}"
fi

# Instructions for starting services
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   How to Start Services${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${BLUE}Option 1: Using tmux (Recommended)${NC}"
echo "--------------------------------"
echo "1. Start tmux: tmux new -s backend"
echo "2. Start Celery worker (Modem):"
echo "   ${GREEN}./modem/run.sh${NC}"
echo "3. Create new pane: Ctrl+B %"
echo "4. Start FastAPI gateway:"
echo "   ${GREEN}./gateway/run.sh${NC}"
echo "5. Detach from tmux: Ctrl+B D"
echo "6. Reattach later: tmux attach -t backend"

echo -e "\n${BLUE}Option 2: Using separate terminals${NC}"
echo "--------------------------------"
echo "Terminal 1 - Start Celery Worker (Modem):"
echo "  ${GREEN}cd $(pwd)${NC}"
echo "  ${GREEN}./modem/run.sh${NC}"
echo ""
echo "Terminal 2 - Start FastAPI Gateway:"
echo "  ${GREEN}cd $(pwd)${NC}"
echo "  ${GREEN}./gateway/run.sh${NC}"

echo -e "\n${BLUE}Option 3: Quick start (both in background)${NC}"
echo "--------------------------------"
echo "  ${GREEN}./modem/run.sh > modem.log 2>&1 &${NC}"
echo "  ${GREEN}./gateway/run.sh${NC}"

# Check if services are already running
echo -e "\n${BLUE}Current Service Status:${NC}"
echo "--------------------------------"

if check_service 8000; then
    echo -e "${GREEN}✓${NC} FastAPI Gateway (port 8000)"
else
    echo -e "${YELLOW}✗${NC} FastAPI Gateway (port 8000)"
fi

# Check if Celery is running
if pgrep -f "celery.*modem.core.main:app.*worker" > /dev/null; then
    echo -e "${GREEN}✓${NC} Celery Worker (Modem)"
else
    echo -e "${YELLOW}✗${NC} Celery Worker (Modem)"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   Service URLs${NC}"
echo -e "${GREEN}========================================${NC}"
echo "• FastAPI Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo "• RabbitMQ Management: ${BLUE}http://localhost:15672${NC} (guest/guest)"
echo "• Flower (if started): ${BLUE}http://localhost:5555${NC}"

echo -e "\n${YELLOW}Tips:${NC}"
echo "• Check logs: tail -f modem.log or tail -f gateway.log"
echo "• Stop all: pkill -f celery && pkill -f uvicorn"
echo "• Monitor Celery: poetry run celery -A modem.core.main:app flower"

echo -e "\n${GREEN}Ready to start services!${NC}"