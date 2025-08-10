from typing import Optional
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
from gateway.service.agent_event_stream_service import (
    AgentEventStreamService,
    StreamConnectionException,
    StreamTimeoutException,
    StreamRedisException,
    StreamClientDisconnectedException
)

router = APIRouter()
logger = get_logger("gateway.controller.agent_thread_controller")

# Global service instances
_thread_service = None
_stream_service = None


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


async def get_stream_service():
    """Get global stream service instance"""
    global _stream_service
    if _stream_service is None:
        logger.info("Creating global stream service instance")
        try:
            _stream_service = AgentEventStreamService()
            await _stream_service.initialize()
            logger.info("Stream service instance created successfully")
        except StreamRedisException as e:
            logger.error(f"Stream service initialization failed, Redis connection error: {e}")
            raise HTTPException(status_code=503, detail=f"Service unavailable, Redis connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Stream service initialization failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")
    return _stream_service


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
    request: Request,
    thread_id: str,
    last_id: Optional[str] = None,
    thread_service: AgentThreadService = Depends(get_thread_service),
    stream_service: AgentEventStreamService = Depends(get_stream_service)
):
    """
    SSE endpoint: Stream events for a specific thread
    
    Args:
        request: FastAPI request object
        thread_id: Thread identifier
        last_id: Last read message ID (optional, for resuming)
        thread_service: Thread service instance (dependency injection)
        stream_service: Stream service instance (dependency injection)
    
    Returns:
        StreamingResponse: SSE stream
    """
    logger.info(
        f"Client requesting SSE connection for thread {thread_id}, last_id={last_id}, "
        f"client_host={request.client.host if request.client else 'unknown'}"
    )
    
    try:
        # Validate thread exists
        if not await thread_service.validate_thread(thread_id):
            logger.warning(f"Thread not found: {thread_id}")
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
        
        # Create SSE response stream using thread-based streaming
        event_stream = stream_service.stream_thread_events(
            request=request,
            thread_id=thread_id,
            last_id=last_id.strip() if last_id else None
        )
        
        logger.info(f"SSE connection established for thread: {thread_id}")
        
        # Return streaming response
        response = StreamingResponse(
            content=event_stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            },
        )
        
        return response
        
    except HTTPException:
        raise
    except StreamClientDisconnectedException as e:
        logger.info(f"Client disconnected from thread {thread_id}: {str(e)}")
        raise HTTPException(status_code=499, detail="Client disconnected")
    except StreamTimeoutException as e:
        logger.warning(f"SSE connection timeout for thread {thread_id}: {str(e)}")
        raise HTTPException(status_code=408, detail=str(e))
    except StreamRedisException as e:
        logger.error(f"Redis error for thread {thread_id}: {str(e)}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except StreamConnectionException as e:
        logger.error(f"Connection error for thread {thread_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Connection error")
    except Exception as e:
        logger.error(f"Unexpected error for thread {thread_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        logger.debug(f"SSE connection handling completed for thread: {thread_id}")