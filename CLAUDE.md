# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Usebase Agent system built with Python, featuring a microservices architecture with three main components:
- **Gateway**: FastAPI service that provides API endpoints and handles SSE event streams
- **Modem**: Celery-based async task processor for workflow execution
- **Workflow**: Core agent logic with LLM integration, tools, and sandbox environments

## Development Setup

### Environment Setup
```bash
# Install dependencies using Poetry
poetry install

# Activate the Poetry environment
poetry shell

# Set up Redis (required for inter-service communication)
brew install redis
brew services start redis
```

### Running Services

Start the Gateway (FastAPI) service:
```bash
cd backend/gateway
./run.sh
# or directly: poetry run uvicorn gateway.core.main:app --reload --host 0.0.0.0 --port 8000
```

Start the Modem (Celery worker) service:
```bash
cd backend/modem  
./run.sh
# or directly: poetry run celery -A modem.core.main:app worker -l INFO
```

### Testing
```bash
# Run tests with pytest
poetry run pytest

# Run tests with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/path/to/test_file.py
```

### Code Quality
```bash
# Run linter
poetry run ruff check .

# Run type checker
poetry run mypy .

# Format code (ruff also handles formatting)
poetry run ruff format .
```

## Architecture

### Service Communication Flow
1. Client sends requests to **Gateway** (port 8000)
2. Gateway publishes tasks to Redis/Celery queue
3. **Modem** workers pick up tasks and execute workflows
4. Workflows use **LLM** (via LiteLLM) and various **Tools**
5. Results stream back through Redis pub/sub to Gateway SSE endpoints

### Key Components

**Gateway** (`backend/gateway/`)
- FastAPI application handling HTTP/SSE endpoints
- Controllers: `agent_event_stream_controller.py`, `health_controller.py`
- Service layer for Redis pub/sub communication

**Modem** (`backend/modem/`)
- Celery worker processing async tasks
- Executes workflow runners
- Manages task lifecycle and error handling

**Workflow** (`backend/workflow/`)
- `agent/`: Core agent implementation with LLM integration
- `tool/`: Extensive tool library (bash, file operations, search, planning)
- `service/`: Sandbox environments (Daytona, E2B)
- `llm/`: LLM abstraction layer using LiteLLM
- `storage/`: Data persistence (job states, user data)

### Tool System
The agent has access to numerous tools organized in `backend/workflow/tool/`:
- File operations: read, write, edit, multi_edit
- Search: grep, glob, ls, web_search
- Execution: bash commands, app serving
- Planning: job_plan, todo management, suggest_next_steps
- Templates: use_template for project scaffolding

### Configuration
- Main config: `backend/config.toml`
- Environment-specific settings via `ENV` variable
- Redis configuration for inter-service communication
- LLM provider settings (supports multiple providers via LiteLLM)

## Important Patterns

### Tool Registration
Tools are registered in `backend/workflow/tool/registry.py` and must extend the base `Tool` class.

### Message Passing
Uses Redis pub/sub for real-time event streaming between services. Events are JSON-encoded and follow SSE format.

### Error Handling
Comprehensive error handling with retry logic (using tenacity) for LLM calls and external service interactions.

### Sandbox Execution
Supports multiple sandbox providers (Daytona, E2B) for secure code execution, configured via `backend/workflow/service/`.

## Database Dependencies
- **Redis**: Required for Celery task queue and pub/sub messaging
- **MongoDB**: Referenced in setup but usage not evident in core services
- **PostgreSQL**: Database connections configured but optional