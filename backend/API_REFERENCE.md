# API Reference Documentation

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API does not require authentication for local development. Production deployments should implement JWT or API key authentication.

---

## Health Check Endpoint

### GET `/health`
Check the health status of the system.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "config_status": {
    "overall_status": "healthy",
    "redis": "connected",
    "celery": "running"
  }
}
```

---

## Thread-Based Agent API

These are the new, recommended endpoints for interacting with the agent system.

### POST `/api/agent/initiate`
Create a new thread for agent interactions.

**Request Body:**
```json
{
  "metadata": {
    "name": "string",           // Optional: Thread name
    "description": "string",    // Optional: Thread description
    "custom_field": "any"       // Optional: Any custom metadata
  },
  "context": {
    "key": "value"             // Optional: Initial context data
  }
}
```

**Response:** `200 OK`
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-15T10:30:00",
  "status": "active"
}
```

**Error Responses:**
- `500` - Failed to create thread

---

### POST `/api/agent/{thread_id}/execute`
Execute a task within the specified thread.

**Path Parameters:**
- `thread_id` (string, required) - The thread identifier

**Request Body:**
```json
{
  "task": "string",                    // Required: Task description
  "context_data": [                    // Optional: Context for the task
    {
      "type": "string",
      "content": "string"
    }
  ],
  "parameters": {                      // Optional: Task parameters
    "key": "value"
  },
  "user_uuid": "string"                // Optional: User identifier
}
```

**Response:** `200 OK`
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "processing",
  "created_at": "2024-01-15T10:31:00"
}
```

**Error Responses:**
- `404` - Thread not found or inactive
- `500` - Failed to execute task

---

### GET `/api/agent/{thread_id}/stream`
Stream Server-Sent Events (SSE) for a specific thread.

**Path Parameters:**
- `thread_id` (string, required) - The thread identifier

**Query Parameters:**
- `last_id` (string, optional) - Resume from specific message ID

**Response:** `200 OK` (SSE Stream)
```
event: waiting
data: {"time": "2024-01-15T10:31:00Z"}

event: task_agent_execute
data: {"type": "thinking", "content": "Analyzing the request..."}

event: task_agent_execute
data: {"type": "tool_use", "tool": "FileReadTool", "input": {"file": "main.py"}}

event: task_agent_execute
data: {"type": "result", "content": "Task completed successfully"}

event: keep_alive
data: {"time": "2024-01-15T10:31:30Z"}
```

**SSE Event Types:**
- `waiting` - Stream is waiting for data
- `keep_alive` - Heartbeat to maintain connection
- `task_agent_execute` - Agent execution updates
- `error` - Error occurred during execution

**Error Responses:**
- `404` - Thread not found
- `408` - Request timeout (no data for extended period)
- `499` - Client disconnected
- `503` - Service unavailable (Redis connection failed)

---

## Legacy Flow-Based API

These endpoints are maintained for backward compatibility but are not recommended for new implementations.

### GET `/agent/event-stream`
Stream SSE events for a flow-based execution.

**Query Parameters:**
- `flowUuid` (string, required) - Flow identifier
- `flowInputUuid` (string, required) - Flow input identifier
- `last_id` (string, optional) - Resume from specific message ID

**Response:** `200 OK` (SSE Stream)
Similar to thread-based streaming but uses flow identifiers.

**Error Responses:**
- `400` - Invalid parameters
- `408` - Request timeout
- `503` - Service unavailable

---

## Request/Response Models

### ThreadInitRequest
```typescript
interface ThreadInitRequest {
  metadata?: Record<string, any>;  // Optional metadata
  context?: Record<string, any>;   // Optional initial context
}
```

### ThreadInitResponse
```typescript
interface ThreadInitResponse {
  thread_id: string;               // UUID
  created_at: string;              // ISO 8601 timestamp
  status: "active" | "inactive";   // Thread status
}
```

### ThreadExecuteRequest
```typescript
interface ThreadExecuteRequest {
  task: string;                    // Task description
  context_data?: Array<{           // Optional context
    type: string;
    content: string;
    [key: string]: any;
  }>;
  parameters?: Record<string, any>; // Optional parameters
  user_uuid?: string;               // Optional user ID
}
```

### ThreadExecuteResponse
```typescript
interface ThreadExecuteResponse {
  thread_id: string;               // Thread UUID
  run_id: string;                  // Run UUID
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;              // ISO 8601 timestamp
}
```

---

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Rate Limiting

Currently, no rate limiting is implemented. For production:
- Recommended: 100 requests/minute per IP
- SSE connections: Max 10 concurrent per user

---

## SSE Connection Management

### Connection Lifecycle
1. Client establishes SSE connection
2. Server sends initial `waiting` event
3. Data events stream as available
4. `keep_alive` events sent every 30 seconds
5. Connection closes on timeout or client disconnect

### Reconnection Strategy
```javascript
// Example client-side reconnection
const eventSource = new EventSource(`/api/agent/${threadId}/stream?last_id=${lastEventId}`);

eventSource.onerror = (error) => {
  if (eventSource.readyState === EventSource.CLOSED) {
    // Reconnect with exponential backoff
    setTimeout(() => {
      reconnect(lastEventId);
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
  }
};
```

### Timeout Configuration
- Business message timeout: 5 minutes (configurable)
- Connection max duration: 30 minutes (configurable)
- Keep-alive interval: 30 seconds

---

## Usage Examples

### Python Example
```python
import httpx
import json

# Create a thread
async with httpx.AsyncClient() as client:
    # 1. Initialize thread
    response = await client.post(
        "http://localhost:8000/api/agent/initiate",
        json={"metadata": {"name": "My Task"}}
    )
    thread_id = response.json()["thread_id"]
    
    # 2. Execute task
    response = await client.post(
        f"http://localhost:8000/api/agent/{thread_id}/execute",
        json={
            "task": "Write a Python hello world function",
            "context_data": [{"type": "instruction", "content": "Make it simple"}]
        }
    )
    run_id = response.json()["run_id"]
    
    # 3. Stream results
    async with client.stream(
        "GET",
        f"http://localhost:8000/api/agent/{thread_id}/stream"
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data:"):
                data = json.loads(line[5:])
                print(data)
```

### JavaScript/TypeScript Example
```typescript
// Create thread
const initResponse = await fetch('/api/agent/initiate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ metadata: { name: 'My Task' } })
});
const { thread_id } = await initResponse.json();

// Execute task
const execResponse = await fetch(`/api/agent/${thread_id}/execute`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    task: 'Write a hello world function',
    context_data: [{ type: 'instruction', content: 'Make it simple' }]
  })
});
const { run_id } = await execResponse.json();

// Stream results
const eventSource = new EventSource(`/api/agent/${thread_id}/stream`);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### cURL Examples
```bash
# Create thread
curl -X POST http://localhost:8000/api/agent/initiate \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"name": "Test Thread"}}'

# Execute task (replace THREAD_ID)
curl -X POST http://localhost:8000/api/agent/THREAD_ID/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write hello world",
    "context_data": [{"type": "instruction", "content": "Python"}]
  }'

# Stream results (replace THREAD_ID)
curl -N http://localhost:8000/api/agent/THREAD_ID/stream
```

---

## WebSocket Support (Future)

WebSocket support is planned for bidirectional communication:
```
ws://localhost:8000/ws/agent/{thread_id}
```

This will enable:
- Real-time bidirectional messaging
- Interactive agent responses
- Progress updates
- Cancel/interrupt operations

---

## Versioning

The API currently does not use versioning. Future versions will use:
- URL versioning: `/api/v2/agent/...`
- Header versioning: `API-Version: 2`

---

## Support

For issues or questions:
- GitHub Issues: [Project Repository]
- Documentation: This file and BACKEND_ARCHITECTURE.md
- Logs: Check `backend/logs/` for detailed error information