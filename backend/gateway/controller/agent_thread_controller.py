import asyncio
import json
from typing import Optional, AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request
from starlette.responses import StreamingResponse

from common.utils.logger_utils import get_logger
from common.type.thread import (
    ThreadInitRequest,
    ThreadInitResponse,
    ThreadExecuteRequest,
    ThreadExecuteResponse,
    ThreadStatus,
    ThreadRunStatus
)
from gateway.service.agent_thread_service import AgentThreadService

router = APIRouter()
logger = get_logger("gateway.controller.agent_thread_controller")

# Global service instances
_thread_service = None


async def get_thread_service():
    """Get global thread service instance"""
    global _thread_service
    if _thread_service is None:
        logger.info("Creating global thread service instance")
        try:
            _thread_service = AgentThreadService()
            await _thread_service.initialize()
            logger.info("Thread service instance created successfully")
        except Exception as e:
            logger.error(f"Thread service initialization failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")
    return _thread_service


@router.post("/initiate", response_model=ThreadInitResponse)
async def initiate_thread(
    request: ThreadInitRequest,
    service: AgentThreadService = Depends(get_thread_service)
):
    """
    Initialize a new agent thread
    
    Args:
        request: Thread initialization request
        service: Thread service instance (dependency injection)
    
    Returns:
        ThreadInitResponse: Thread ID and metadata
    """
    try:
        logger.info(f"Initiating new thread with metadata: {request.metadata}")
        
        # Create new thread
        thread_id = await service.create_thread(
            metadata=request.metadata,
            context=request.context
        )
        
        response = ThreadInitResponse(
            thread_id=thread_id,
            created_at=datetime.utcnow().isoformat(),
            status=ThreadStatus.ACTIVE
        )
        
        logger.info(f"Thread created successfully: {thread_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to create thread: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {str(e)}")


@router.post("/{thread_id}/execute", response_model=ThreadExecuteResponse)
async def execute_agent_task(
    thread_id: str,
    request: ThreadExecuteRequest,
    service: AgentThreadService = Depends(get_thread_service)
):
    """
    Execute an agent task in the specified thread
    
    Args:
        thread_id: Thread identifier
        request: Task execution request
        service: Thread service instance (dependency injection)
    
    Returns:
        ThreadExecuteResponse: Run ID and status
    """
    try:
        logger.info(f"Executing task in thread {thread_id}: {request.task}")
        
        # Validate thread exists and is active
        if not await service.validate_thread(thread_id):
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found or inactive")
        
        # Execute task
        run_id = await service.execute_task(
            thread_id=thread_id,
            task=request.task,
            context_data=request.context_data,
            parameters=request.parameters,
            user_uuid=request.user_uuid
        )
        
        response = ThreadExecuteResponse(
            thread_id=thread_id,
            run_id=run_id,
            status=ThreadRunStatus.PROCESSING,
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Task execution started - thread: {thread_id}, run: {run_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute task in thread {thread_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@router.get("/{thread_id}/stream")
async def stream_thread_events(
    thread_id: str,
    request: Request,
    last_id: Optional[str] = None,
    service: AgentThreadService = Depends(get_thread_service)
):
    """
    Stream Server-Sent Events for a specific thread using Redis Lists and Pub/Sub
    
    Args:
        thread_id: Thread identifier
        request: FastAPI request object
        last_id: Last processed message index (optional, for resuming)
        service: Thread service instance (dependency injection)
    
    Returns:
        StreamingResponse: SSE stream
    """
    logger.info(
        f"Client requesting SSE connection for thread {thread_id}, last_id={last_id}, "
        f"client_host={request.client.host if request.client else 'unknown'}"
    )
    
    try:
        # Validate thread exists
        if not await service.validate_thread(thread_id):
            logger.warning(f"Thread not found: {thread_id}")
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
        
        # Create SSE response stream
        async def stream_generator() -> AsyncGenerator[str, None]:
            """Generate SSE events from Redis List and Pub/Sub"""
            logger.debug(f"Starting stream for thread {thread_id}")
            
            response_list_key = f"agent_run:{thread_id}:responses"
            response_channel = f"agent_run:{thread_id}:new_response"
            control_channel = f"agent_run:{thread_id}:control"
            
            last_processed_index = int(last_id) if last_id else -1
            pubsub_response = None
            pubsub_control = None
            listener_task = None
            terminate_stream = False
            initial_yield_complete = False
            
            try:
                # Get Redis client
                redis = service.redis
                
                # 1. Fetch and yield initial responses from Redis list
                initial_responses_json = await redis.lrange(response_list_key, 0, -1)
                if initial_responses_json:
                    initial_responses = [json.loads(r) for r in initial_responses_json]
                    logger.debug(f"Sending {len(initial_responses)} initial responses for {thread_id}")
                    
                    # Skip already processed messages if last_id provided
                    start_index = last_processed_index + 1 if last_processed_index >= 0 else 0
                    for idx, response in enumerate(initial_responses[start_index:], start=start_index):
                        yield f"data: {json.dumps(response)}\n\n"
                        last_processed_index = idx
                        
                        # Check for completion status
                        if response.get('type') == 'status' and response.get('status') in ['completed', 'failed', 'stopped']:
                            logger.info(f"Detected completion status in initial messages: {response.get('status')}")
                            terminate_stream = True
                            break
                
                initial_yield_complete = True
                
                if terminate_stream:
                    yield f"data: {json.dumps({'type': 'status', 'status': 'completed'})}\n\n"
                    return
                
                # 2. Check if client is still connected
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from thread {thread_id}")
                    return
                
                # 3. Set up Pub/Sub listeners for new responses and control signals
                pubsub_response = redis.pubsub()
                await pubsub_response.subscribe(response_channel)
                logger.debug(f"Subscribed to response channel: {response_channel}")
                
                pubsub_control = redis.pubsub()
                await pubsub_control.subscribe(control_channel)
                logger.debug(f"Subscribed to control channel: {control_channel}")
                
                # Queue for communication between listeners and main loop
                message_queue = asyncio.Queue()
                
                async def listen_messages():
                    """Listen for Redis Pub/Sub messages"""
                    try:
                        # Create tasks for both channels
                        async def listen_response():
                            async for message in pubsub_response.listen():
                                if message['type'] == 'message':
                                    await message_queue.put({'type': 'new_response', 'data': message['data']})
                        
                        async def listen_control():
                            async for message in pubsub_control.listen():
                                if message['type'] == 'message':
                                    await message_queue.put({'type': 'control', 'data': message['data']})
                                    return  # Stop on control signal
                        
                        # Run both listeners concurrently
                        await asyncio.gather(
                            listen_response(),
                            listen_control(),
                            return_exceptions=True
                        )
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.error(f"Listener error for {thread_id}: {e}")
                        await message_queue.put({'type': 'error', 'data': str(e)})
                
                listener_task = asyncio.create_task(listen_messages())
                
                # 4. Main loop to process messages
                while not terminate_stream:
                    try:
                        # Check client connection
                        if await request.is_disconnected():
                            logger.info(f"Client disconnected from thread {thread_id}")
                            terminate_stream = True
                            break
                        
                        # Wait for new messages with timeout
                        try:
                            queue_item = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                        except asyncio.TimeoutError:
                            # Send keep-alive
                            yield f"data: {json.dumps({'type': 'keep_alive', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                            continue
                        
                        if queue_item['type'] == 'new_response':
                            # Fetch new responses from Redis list
                            new_start_index = last_processed_index + 1
                            new_responses_json = await redis.lrange(response_list_key, new_start_index, -1)
                            
                            if new_responses_json:
                                new_responses = [json.loads(r) for r in new_responses_json]
                                for idx, response in enumerate(new_responses, start=new_start_index):
                                    yield f"data: {json.dumps(response)}\n\n"
                                    last_processed_index = idx
                                    
                                    # Check for completion
                                    if response.get('type') == 'status' and response.get('status') in ['completed', 'failed', 'stopped']:
                                        logger.info(f"Detected completion status: {response.get('status')}")
                                        terminate_stream = True
                                        break
                        
                        elif queue_item['type'] == 'control':
                            control_signal = queue_item['data']
                            logger.info(f"Received control signal '{control_signal}' for {thread_id}")
                            terminate_stream = True
                            
                            # Map control signals to status
                            status_map = {
                                'STOP': 'stopped',
                                'END_STREAM': 'completed',
                                'ERROR': 'failed'
                            }
                            status = status_map.get(control_signal, 'completed')
                            yield f"data: {json.dumps({'type': 'status', 'status': status})}\n\n"
                            break
                        
                        elif queue_item['type'] == 'error':
                            logger.error(f"Listener error for {thread_id}: {queue_item['data']}")
                            terminate_stream = True
                            yield f"data: {json.dumps({'type': 'status', 'status': 'error', 'message': queue_item['data']})}\n\n"
                            break
                    
                    except asyncio.CancelledError:
                        logger.info(f"Stream cancelled for {thread_id}")
                        terminate_stream = True
                        break
                    except Exception as e:
                        logger.error(f"Stream error for {thread_id}: {e}", exc_info=True)
                        terminate_stream = True
                        yield f"data: {json.dumps({'type': 'status', 'status': 'error', 'message': str(e)})}\n\n"
                        break
            
            except Exception as e:
                logger.error(f"Error setting up stream for thread {thread_id}: {e}", exc_info=True)
                if not initial_yield_complete:
                    yield f"data: {json.dumps({'type': 'status', 'status': 'error', 'message': f'Failed to start stream: {e}'})}\n\n"
            
            finally:
                # Cleanup
                terminate_stream = True
                
                if pubsub_response:
                    await pubsub_response.unsubscribe(response_channel)
                    await pubsub_response.close()
                
                if pubsub_control:
                    await pubsub_control.unsubscribe(control_channel)
                    await pubsub_control.close()
                
                if listener_task:
                    listener_task.cancel()
                    try:
                        await listener_task
                    except asyncio.CancelledError:
                        pass
                
                logger.debug(f"Stream cleanup complete for thread {thread_id}")
        
        # Return streaming response
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error for thread {thread_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")