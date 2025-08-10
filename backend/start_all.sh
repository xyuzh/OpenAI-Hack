#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Starting All Backend Services${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check if a service is running
check_service() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Start RabbitMQ if not running
echo -e "\n${BLUE}Starting RabbitMQ...${NC}"
if check_service 5672; then
    echo -e "${GREEN}✓${NC} RabbitMQ already running"
else
    if command -v rabbitmq-server &> /dev/null; then
        echo "Starting RabbitMQ in background..."
        rabbitmq-server -detached
        sleep 3
        echo -e "${GREEN}✓${NC} RabbitMQ started"
    else
        echo -e "${RED}✗ RabbitMQ not installed${NC}"
        exit 1
    fi
fi

# Start Redis if not running
echo -e "\n${BLUE}Starting Redis...${NC}"
if check_service 6379; then
    echo -e "${GREEN}✓${NC} Redis already running"
else
    if command -v redis-server &> /dev/null; then
        echo "Starting Redis in background..."
        redis-server --daemonize yes
        sleep 2
        echo -e "${GREEN}✓${NC} Redis started"
    else
        echo -e "${RED}✗ Redis not installed${NC}"
        exit 1
    fi
fi

# Check if tmux is available
if command -v tmux &> /dev/null; then
    # Check if backend session already exists
    if tmux has-session -t backend 2>/dev/null; then
        echo -e "\n${YELLOW}tmux session 'backend' already exists${NC}"
        echo "Attach to it with: tmux attach -t backend"
        echo "Or kill it with: tmux kill-session -t backend"
        exit 1
    fi
    
    echo -e "\n${GREEN}Starting services in tmux session 'backend'...${NC}"
    
    # Create new tmux session and start modem
    tmux new-session -d -s backend -n services
    tmux send-keys -t backend:services "cd $(pwd)" C-m
    tmux send-keys -t backend:services "./modem/run.sh" C-m
    
    # Split window and start gateway
    tmux split-window -h -t backend:services
    tmux send-keys -t backend:services.1 "cd $(pwd)" C-m
    tmux send-keys -t backend:services.1 "./gateway/run.sh" C-m
    
    # Give services time to start
    sleep 3
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All services started successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Services are running in tmux session 'backend'"
    echo ""
    echo -e "${BLUE}Commands:${NC}"
    echo "• Attach to session: ${GREEN}tmux attach -t backend${NC}"
    echo "• Detach from session: ${GREEN}Ctrl+B, D${NC}"
    echo "• Switch panes: ${GREEN}Ctrl+B, arrow keys${NC}"
    echo "• Kill session: ${GREEN}tmux kill-session -t backend${NC}"
    echo ""
    echo -e "${BLUE}Service URLs:${NC}"
    echo "• FastAPI Docs: ${GREEN}http://localhost:8000/docs${NC}"
    echo "• RabbitMQ Management: ${GREEN}http://localhost:15672${NC}"
    echo ""
    echo -e "${YELLOW}Attaching to tmux session in 3 seconds...${NC}"
    sleep 3
    tmux attach -t backend
    
else
    # Fallback to running in background without tmux
    echo -e "\n${YELLOW}tmux not found. Starting services in background...${NC}"
    
    # Kill any existing services
    pkill -f "celery.*modem.core.main:app.*worker" 2>/dev/null
    pkill -f "uvicorn.*gateway.core.main:app" 2>/dev/null
    
    # Start modem in background
    echo -e "\n${BLUE}Starting Celery Worker (Modem)...${NC}"
    ./modem/run.sh > modem.log 2>&1 &
    MODEM_PID=$!
    echo "Modem started with PID: $MODEM_PID (logs in modem.log)"
    
    # Start gateway in foreground
    echo -e "\n${BLUE}Starting FastAPI Gateway...${NC}"
    echo -e "${YELLOW}Gateway will run in foreground. Press Ctrl+C to stop all services.${NC}"
    echo ""
    
    # Trap Ctrl+C to cleanup
    trap cleanup INT
    
    cleanup() {
        echo -e "\n${YELLOW}Shutting down services...${NC}"
        
        # Kill modem
        kill $MODEM_PID 2>/dev/null
        
        # Kill any remaining processes
        pkill -f "celery.*modem.core.main:app.*worker" 2>/dev/null
        
        echo -e "${GREEN}Services stopped.${NC}"
        exit 0
    }
    
    # Give modem time to start
    sleep 3
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Services starting...${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Service URLs:${NC}"
    echo "• FastAPI Docs: ${GREEN}http://localhost:8000/docs${NC}"
    echo "• RabbitMQ Management: ${GREEN}http://localhost:15672${NC}"
    echo ""
    echo "• Check Modem logs: ${GREEN}tail -f modem.log${NC}"
    echo ""
    
    # Run gateway in foreground
    ./gateway/run.sh
fi