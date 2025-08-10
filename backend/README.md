# Backend Services

This backend provides thread-based API endpoints for agent operations with Composio integration for OAuth authentication and document management.

## Architecture

- **Gateway** (FastAPI) - API server on port 8000
- **Modem** (Celery) - Task worker for processing agent requests  
- **RabbitMQ** - Message broker for Celery
- **Redis** - Result backend and streaming data store

## Quick Start

### 1. Prerequisites

Install required services:
```bash
brew install rabbitmq redis poetry
brew services start rabbitmq
brew services start redis
```

### 2. Python Environment Setup

```bash
poetry install
```

### 3. Configuration

Copy environment template and add your API keys:
```bash
cp .env.complete .env
# Edit .env to add:
# - OPENAI_API_KEY
# - COMPOSIO_API_KEY
```

### 4. Start Services

#### Option A: Check prerequisites first
```bash
./start_services.sh  # Shows status and instructions
```

#### Option B: Start all automatically
```bash
./start_all.sh  # Starts everything in tmux
```

#### Option C: Start manually
```bash
# Terminal 1 - Celery Worker
./modem/run.sh

# Terminal 2 - FastAPI Gateway  
./gateway/run.sh
```

## API Documentation

- **API Docs**: http://localhost:8000/docs
- **RabbitMQ**: http://localhost:15672 (guest/guest)

## Main Endpoints

### Thread Management
- `POST /api/agent/initiate` - Create thread
- `POST /api/agent/{thread_id}/execute` - Execute task
- `GET /api/agent/{thread_id}/stream` - Stream results

### Composio Integration
- `POST /api/composio/auth/initiate` - OAuth for Google Docs/Gmail/Linear
- `GET /api/documents` - Fetch Google Docs

## Testing

```bash
poetry run python test_thread_api.py
poetry run python test_rabbitmq.py
```

## Additional Services (Optional)

MongoDB (if needed):
```bash
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

PostgreSQL viewer:
```bash
pgweb --bind=0.0.0.0 --port=8081 --url=postgres://postgres:test@localhost:5432
```

## Documentation

- [RabbitMQ Setup](./RABBITMQ_SETUP.md)
- [Composio Integration](./COMPOSIO_INTEGRATION.md)
- [Architecture Details](./REFACTORING_SUMMARY.md)
