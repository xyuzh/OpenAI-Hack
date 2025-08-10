# Thread-Based Agent API Testing Guide

## API Endpoints

### 1. Initialize Thread
**POST** `/api/agent/initiate`

Creates a new thread for agent interactions.

```bash
curl -X POST http://localhost:8000/api/agent/initiate \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "name": "My Thread",
      "description": "Test thread for demo"
    },
    "context": {
      "user": "test_user"
    }
  }'
```

**Response:**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-15T10:30:00",
  "status": "active"
}
```

### 2. Execute Task
**POST** `/api/agent/{thread_id}/execute`

Executes a task within the specified thread.

```bash
# Replace {thread_id} with actual thread ID from step 1
curl -X POST http://localhost:8000/api/agent/{thread_id}/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Write a Python function to calculate fibonacci",
    "context_data": [
      {
        "type": "instruction",
        "content": "Create an efficient fibonacci function"
      }
    ],
    "parameters": {
      "language": "python",
      "style": "functional"
    }
  }'
```

**Response:**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "processing",
  "created_at": "2024-01-15T10:31:00"
}
```

### 3. Stream Results
**GET** `/api/agent/{thread_id}/stream`

Streams server-sent events (SSE) for the thread.

```bash
# Basic streaming
curl -N http://localhost:8000/api/agent/{thread_id}/stream

# With last event ID for resuming
curl -N http://localhost:8000/api/agent/{thread_id}/stream?last_id=1234567890
```

**Response (SSE Stream):**
```
event: waiting
data: {"time": "2024-01-15T10:31:00Z"}

event: task_agent_execute
data: {"type": "thinking", "content": "Analyzing the request..."}

event: task_agent_execute
data: {"type": "code", "content": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"}

event: keep_alive
data: {"time": "2024-01-15T10:31:30Z"}
```

## Testing Workflow

### Step 1: Start the Gateway Service
```bash
cd backend/gateway
./run.sh
```

### Step 2: Start the Modem Service (in another terminal)
```bash
cd backend/modem
./run.sh
```

### Step 3: Run Automated Tests
```bash
cd backend
python test_thread_api.py
```

### Step 4: Manual Testing with curl

1. Create a thread:
```bash
THREAD_ID=$(curl -s -X POST http://localhost:8000/api/agent/initiate \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"name": "Test"}}' \
  | jq -r '.thread_id')

echo "Thread ID: $THREAD_ID"
```

2. Execute a task:
```bash
RUN_ID=$(curl -s -X POST http://localhost:8000/api/agent/$THREAD_ID/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Say hello",
    "context_data": [{"type": "greeting", "content": "Hello World"}]
  }' \
  | jq -r '.run_id')

echo "Run ID: $RUN_ID"
```

3. Stream results:
```bash
curl -N http://localhost:8000/api/agent/$THREAD_ID/stream
```

## Error Handling

### Common Error Responses

**404 - Thread Not Found**
```json
{
  "detail": "Thread {thread_id} not found or inactive"
}
```

**408 - Request Timeout**
```json
{
  "detail": "Stream timeout: No messages received for 5 minutes"
}
```

**500 - Internal Server Error**
```json
{
  "detail": "Failed to execute task: {error_message}"
}
```

**503 - Service Unavailable**
```json
{
  "detail": "Service unavailable, Redis connection failed"
}
```

## Notes

- Thread IDs are UUIDs and remain active for 7 days
- Each thread can handle multiple task executions
- The SSE stream uses the same Redis stream for all runs in a thread
- Keep-alive events are sent every 30 seconds to maintain the connection
- The stream endpoint supports resuming from a specific message ID using the `last_id` parameter