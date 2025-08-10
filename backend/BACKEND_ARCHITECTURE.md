# Backend Architecture Documentation

## Overview

The backend system implements an AI agent platform with a microservices architecture consisting of three main components:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Gateway   │────▶│    Modem    │────▶│  Workflow   │
│  (FastAPI)  │     │  (Celery)   │     │   (Agent)   │
└─────────────┘     └─────────────┘     └─────────────┘
       ▲                    │                    │
       │                    ▼                    ▼
       │              ┌─────────────┐     ┌─────────────┐
       └──────────────│    Redis    │     │     LLM     │
                      └─────────────┘     └─────────────┘
```

## Components

### 1. Gateway Service (`backend/gateway/`)
**Purpose**: API Gateway handling HTTP/SSE endpoints and client connections

**Technology Stack**:
- FastAPI for REST APIs
- Server-Sent Events (SSE) for real-time streaming
- Redis for pub/sub messaging

**Key Files**:
- `core/main.py` - FastAPI application setup
- `controller/` - API endpoint controllers
- `service/` - Business logic services

### 2. Modem Service (`backend/modem/`)
**Purpose**: Asynchronous task processor using Celery

**Technology Stack**:
- Celery for distributed task queue
- Redis as message broker
- Async task execution

**Key Files**:
- `core/main.py` - Celery app configuration
- `type/flow_type.py` - Request/response models

### 3. Workflow Service (`backend/workflow/`)
**Purpose**: Core agent logic, LLM integration, and tool execution

**Technology Stack**:
- LiteLLM for multi-provider LLM support
- Custom tool framework
- Sandbox environments (Daytona, E2B)

**Key Components**:
- `agent/` - Agent implementation with planning and execution
- `llm/` - LLM abstraction layer
- `tool/` - Extensible tool system
- `runner/` - Task execution runner
- `service/` - External service integrations

## API Endpoints

### Health Check
- **GET** `/health` - System health status

### Legacy Flow-based Endpoints
- **GET** `/agent/event-stream` - SSE stream for flow-based events
  - Query params: `flowUuid`, `flowInputUuid`, `last_id`

### Thread-based Endpoints (New)
- **POST** `/api/agent/initiate` - Create a new thread
  - Returns: `thread_id`
  
- **POST** `/api/agent/{thread_id}/execute` - Execute task in thread
  - Returns: `run_id` and status
  
- **GET** `/api/agent/{thread_id}/stream` - SSE stream for thread events
  - Query params: `last_id` (optional)

## Data Flow

### 1. Thread Initiation
```
Client → POST /api/agent/initiate
       → Gateway creates thread in Redis
       → Returns thread_id to client
```

### 2. Task Execution
```
Client → POST /api/agent/{thread_id}/execute
       → Gateway publishes to Celery queue
       → Modem picks up task
       → Runner initializes Agent
       → Agent executes with LLM + Tools
       → Results stream to Redis
```

### 3. Result Streaming
```
Client → GET /api/agent/{thread_id}/stream (SSE)
       ← Gateway reads from Redis stream
       ← Real-time events via SSE
```

## Agent System

### Agent Class (`workflow/agent/agent.py`)
The Agent manages the interaction between LLM and tools:

**Planning Tools**:
- `JobPlanTool` - Creates execution plans

**Execution Tools**:
- `BashTool` - Execute shell commands
- `FileReadTool` - Read files
- `FileEditTool` - Edit files
- `FilesCreationTool` - Create multiple files
- `MultiEditTool` - Multiple edits in one operation
- `GrepTool` - Search file contents
- `GlobTool` - File pattern matching
- `LsTool` - List directory contents
- `WebSearchTool` - Web search capabilities
- `UseTemplateTool` - Apply code templates
- `TodoReadTool`/`TodoWriteTool` - Task management
- `SuggestNextStepsTool` - AI suggestions
- `UrlExposeTool` - URL exposure for apps

### LLM Integration
- **Provider**: LiteLLM (supports multiple providers)
- **Models**: Configurable via `config.toml`
- **Default**: Claude Sonnet 3.7 for execution
- **Features**:
  - Prompt caching
  - Retry logic with exponential backoff
  - Token management
  - Native tool calling support

### Tool Execution Framework
Each tool extends the base `Tool` class and implements:
- Schema definition (Pydantic models)
- Execution logic
- Error handling
- Result formatting

## Redis Structure

### Thread-based Keys
```
thread:{thread_id}:metadata     # Thread configuration
thread:{thread_id}:stream        # Event stream
thread:{thread_id}:runs          # List of run IDs
thread:{thread_id}:run:{run_id} # Individual run data
```

### Legacy Flow-based Keys
```
stream:{flow_uuid}:{flow_input_uuid} # Legacy stream format
```

## Configuration

### Main Configuration (`backend/config.toml`)
- LLM settings (models, tokens, retry logic)
- Agent configuration
- Sandbox settings
- Tool enablement flags

### Environment Variables
- `ENV` - Environment (local/dev/prod)
- Redis connection settings
- API keys and secrets

## Message Types (SSE Events)

### System Events
- `waiting` - Waiting for task to start
- `keep_alive` - Connection heartbeat
- `error` - Error notifications

### Business Events
- `task_agent_execute` - Agent execution updates
- Custom event types per tool

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad request
- `404` - Thread/Resource not found
- `408` - Request timeout
- `499` - Client disconnected
- `500` - Internal server error
- `503` - Service unavailable (Redis down)

### Retry Mechanisms
- LLM calls: Exponential backoff with configurable retries
- Redis operations: Connection pooling with retry
- Celery tasks: Automatic retry on failure

## Security Features

### CORS Configuration
- Configurable origins
- Credential support
- Method and header allowlisting

### Authentication/Authorization
- JWT support (configurable)
- API key validation
- User UUID tracking

## Monitoring & Logging

### Logging
- Structured logging with `colorlog`
- Component-specific loggers
- Debug/Info/Warning/Error levels

### Health Checks
- Redis connectivity
- Service status
- Configuration validation

## Deployment

### Docker Support
- Dockerfiles for each service
- Environment-specific configurations
- Container orchestration ready

### Scaling Considerations
- Horizontal scaling for Gateway (stateless)
- Celery worker scaling for Modem
- Redis clustering for high availability
- Connection pooling for database operations

## Development Workflow

### Local Development
1. Start Redis: `redis-server`
2. Start Gateway: `cd backend/gateway && ./run.sh`
3. Start Modem: `cd backend/modem && ./run.sh`
4. Test endpoints: `python test_thread_api.py`

### Testing
- Unit tests with pytest
- Integration tests for API endpoints
- Tool execution tests
- LLM mock testing

## Future Enhancements

### Planned Features
- WebSocket support for bidirectional communication
- Enhanced thread context management
- Tool plugin system
- Multi-agent collaboration
- Advanced caching strategies

### Performance Optimizations
- Response streaming optimization
- LLM prompt caching
- Redis pipeline operations
- Connection pool tuning