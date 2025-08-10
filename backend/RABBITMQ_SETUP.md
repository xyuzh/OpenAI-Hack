# RabbitMQ and Celery Setup Instructions

## 1. Install RabbitMQ Locally

### Option A: Using Homebrew (macOS)
```bash
# Install RabbitMQ
brew install rabbitmq

# Start RabbitMQ service
brew services start rabbitmq

# Or start manually (without service)
/opt/homebrew/opt/rabbitmq/sbin/rabbitmq-server
```

### Option B: Using Docker
```bash
# Pull and run RabbitMQ with Management UI
docker run -d \
  --name rabbitmq \
  -p 5672:5672 \
  -p 15672:15672 \
  -e RABBITMQ_DEFAULT_USER=admin \
  -e RABBITMQ_DEFAULT_PASS=admin123 \
  rabbitmq:3-management

# Access Management UI at: http://localhost:15672
# Default credentials: admin/admin123
```

### Option C: Direct Download
1. Download from: https://www.rabbitmq.com/download.html
2. Follow platform-specific installation instructions

## 2. Configure Environment Variables

Add the following RabbitMQ configuration to your `.env` file:

```bash
# RabbitMQ Configuration
RABBITMQ_PROTOCOL=amqp
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest

# For Docker setup, use:
# RABBITMQ_USERNAME=admin
# RABBITMQ_PASSWORD=admin123

# Celery Queue Configuration
CELERY_QUEUE=celery_default_queue
CELERY_EXCHANGE=celery_exchange
CELERY_ROUTING_KEY=celery.default
CELERY_DL_EXCHANGE=celery_dl_exchange
CELERY_DL_ROUTING_KEY=celery.dl
CELERY_MESSAGE_TTL=86400000
CELERY_TASK_CREATE_MISSING_QUEUES=true

# Celery Control & Event Exchanges
CELERY_CONTROL_EXCHANGE=celery_control
CELERY_EVENT_EXCHANGE=celery_event

# Celery Worker Configuration
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_PREFETCH_MULTIPLIER=1
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
CELERY_TASK_TIME_LIMIT=3600
CELERY_TASK_SOFT_TIME_LIMIT=3300

# Redis Configuration (for result backend)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_USERNAME=
REDIS_PASSWORD=
REDIS_DB=0

# PostgreSQL Configuration (if needed)
POSTGRESQL_DATASOURCE_HOST=localhost
POSTGRESQL_DATASOURCE_PORT=5432
POSTGRESQL_DATASOURCE_USERNAME=postgres
POSTGRESQL_DATASOURCE_PASSWORD=postgres
POSTGRESQL_LANGCHAIN_STATE_DATABASE_NAME=langchain_state

# AWS AppSync (if needed)
AWS_APP_SYNC_HTTP_DOMAIN=your-domain.appsync-api.region.amazonaws.com
AWS_APP_SYNC_WEBSOCKET_DOMAIN=your-domain.appsync-realtime-api.region.amazonaws.com
AWS_APP_SYNC_API_KEY=your-api-key

# Usebase Server Boot (if needed)
USEBASE_SERVER_BOOT_BASE_URL=http://localhost:8080
USEBASE_INTERNAL_API_KEY=your-internal-key

# Environment
ENV=local
```

## 3. Verify RabbitMQ is Running

### Check RabbitMQ Status
```bash
# If installed via Homebrew
brew services list | grep rabbitmq

# Check if port 5672 is listening
lsof -i :5672

# Or using netstat
netstat -an | grep 5672
```

### Access RabbitMQ Management UI
Open browser and go to: http://localhost:15672
- Default credentials: guest/guest (for local installation)
- Docker credentials: admin/admin123 (if using Docker)

## 4. Start Redis (Required for Celery Result Backend)

### Using Homebrew
```bash
brew install redis
brew services start redis
```

### Using Docker
```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:latest
```

## 5. Start Celery Worker

### Navigate to backend directory
```bash
cd /Users/xinyu/code/hackthon/openai_hack/backend
```

### Start Celery Worker (Modem)
```bash
# Basic start
poetry run celery -A modem.core.celery_app worker --loglevel=info

# With more options
poetry run celery -A modem.core.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --pool=prefork \
  --autoscale=10,3 \
  -n worker1@%h

# For development with auto-reload
poetry run watchmedo auto-restart \
  --directory=./modem \
  --pattern="*.py" \
  --recursive \
  -- celery -A modem.core.celery_app worker --loglevel=info
```

### Start Celery Beat (if needed for scheduled tasks)
```bash
poetry run celery -A modem.core.celery_app beat --loglevel=info
```

### Start Flower (Celery Monitoring UI)
```bash
poetry run celery -A modem.core.celery_app flower --port=5555

# Access at: http://localhost:5555
```

## 6. Start FastAPI Gateway

```bash
# In another terminal
cd /Users/xinyu/code/hackthon/openai_hack/backend
poetry run python -m gateway.core.main

# Or with uvicorn directly
poetry run uvicorn gateway.core.main:app --reload --host 0.0.0.0 --port 8000
```

## 7. Test the Setup

### Test RabbitMQ Connection
```python
import pika

# Test connection
connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost')
)
channel = connection.channel()
print("Connected to RabbitMQ!")
connection.close()
```

### Test Celery Task
```bash
# Run the test script
poetry run python test_thread_api.py
```

## 8. Troubleshooting

### RabbitMQ Connection Issues
```bash
# Reset RabbitMQ (warning: deletes all data)
rabbitmqctl stop_app
rabbitmqctl reset
rabbitmqctl start_app

# Check RabbitMQ logs
tail -f /opt/homebrew/var/log/rabbitmq/rabbit@*.log
```

### Permission Issues
```bash
# Set proper permissions
rabbitmqctl add_user admin admin123
rabbitmqctl set_user_tags admin administrator
rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"
```

### Port Already in Use
```bash
# Find process using port
lsof -i :5672
# Kill the process
kill -9 <PID>
```

## 9. Complete Startup Sequence

```bash
# Terminal 1: Start RabbitMQ
rabbitmq-server

# Terminal 2: Start Redis
redis-server

# Terminal 3: Start Celery Worker
cd /Users/xinyu/code/hackthon/openai_hack/backend
poetry run celery -A modem.core.celery_app worker --loglevel=info

# Terminal 4: Start FastAPI Gateway
cd /Users/xinyu/code/hackthon/openai_hack/backend
poetry run uvicorn gateway.core.main:app --reload --port 8000

# Terminal 5: (Optional) Start Flower for monitoring
poetry run celery -A modem.core.celery_app flower --port=5555
```

## 10. Environment Variable Summary

The constructed broker URL will be:
```
amqp://guest:guest@localhost:5672
```

Or with Docker:
```
amqp://admin:admin123@localhost:5672
```

This URL is automatically constructed from the environment variables:
- `RABBITMQ_PROTOCOL`: amqp
- `RABBITMQ_USERNAME`: guest/admin
- `RABBITMQ_PASSWORD`: guest/admin123
- `RABBITMQ_HOST`: localhost
- `RABBITMQ_PORT`: 5672

## Quick Start Script

Create a `start_services.sh` script:

```bash
#!/bin/bash

echo "Starting RabbitMQ..."
rabbitmq-server -detached

echo "Starting Redis..."
redis-server --daemonize yes

echo "Waiting for services to start..."
sleep 5

echo "Starting Celery Worker..."
cd /Users/xinyu/code/hackthon/openai_hack/backend
poetry run celery -A modem.core.celery_app worker --loglevel=info --detach

echo "Starting FastAPI Gateway..."
poetry run uvicorn gateway.core.main:app --reload --port 8000
```

Make it executable:
```bash
chmod +x start_services.sh
./start_services.sh
```