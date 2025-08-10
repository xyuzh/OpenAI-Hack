import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from celery import Celery

from common.config import Config
from common.db.redis_pool import get_async_redis_client
from common.utils.logger_utils import get_logger
from common.utils.string_utils import generate_uuid
from common.type.thread import (
    ThreadStatus,
    ThreadRunStatus,
    ThreadMetadata,
    ThreadRun
)
from modem.type.flow_type import ProcessFlowDataRequest

logger = get_logger("gateway.service.agent_thread_service")


class AgentThreadService:
    """Service for managing agent threads and task execution"""
    
    def __init__(self):
        """Initialize thread service"""
        self.redis = None
        self.celery_app = None
        self.initialized = False
        
        # Redis key prefixes
        self.THREAD_PREFIX = "thread"
        self.THREAD_METADATA_SUFFIX = "metadata"
        self.THREAD_RUNS_SUFFIX = "runs"
        self.THREAD_RUN_SUFFIX = "run"
        self.THREAD_STREAM_SUFFIX = "stream"
        
        logger.info("AgentThreadService initialized")
    
    async def initialize(self):
        """Initialize async resources"""
        if not self.initialized:
            try:
                # Get Redis client from pool
                self.redis = await get_async_redis_client()
                
                # Initialize Celery app
                celery_config = Config.get_celery_config()
                self.celery_app = Celery('gateway')
                self.celery_app.conf.update(celery_config)
                
                self.initialized = True
                logger.info("AgentThreadService async resources initialized")
            except Exception as e:
                logger.error(f"AgentThreadService initialization failed: {e}")
                raise
        return self
    
    def _get_thread_metadata_key(self, thread_id: str) -> str:
        """Get Redis key for thread metadata"""
        return f"{self.THREAD_PREFIX}:{thread_id}:{self.THREAD_METADATA_SUFFIX}"
    
    def _get_thread_runs_key(self, thread_id: str) -> str:
        """Get Redis key for thread runs list"""
        return f"{self.THREAD_PREFIX}:{thread_id}:{self.THREAD_RUNS_SUFFIX}"
    
    def _get_thread_run_key(self, thread_id: str, run_id: str) -> str:
        """Get Redis key for specific run"""
        return f"{self.THREAD_PREFIX}:{thread_id}:{self.THREAD_RUN_SUFFIX}:{run_id}"
    
    def _get_thread_stream_key(self, thread_id: str) -> str:
        """Get Redis stream key for thread"""
        return f"{self.THREAD_PREFIX}:{thread_id}:{self.THREAD_STREAM_SUFFIX}"
    
    async def create_thread(
        self,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new thread
        
        Args:
            metadata: Optional metadata for the thread
            context: Optional initial context
        
        Returns:
            str: Thread ID
        """
        try:
            # Generate thread ID
            thread_id = generate_uuid()
            
            # Create thread metadata
            thread_metadata = ThreadMetadata(
                thread_id=thread_id,
                status=ThreadStatus.ACTIVE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata=metadata or {},
                run_count=0,
                last_run_id=None
            )
            
            # Store metadata in Redis
            metadata_key = self._get_thread_metadata_key(thread_id)
            await self.redis.set(
                metadata_key,
                thread_metadata.model_dump_json(),
                ex=86400 * 7  # Expire after 7 days
            )
            
            # Initialize runs list
            runs_key = self._get_thread_runs_key(thread_id)
            await self.redis.expire(runs_key, 86400 * 7)  # Set expiry for runs list
            
            # Store initial context if provided
            if context:
                context_key = f"{self.THREAD_PREFIX}:{thread_id}:context"
                await self.redis.set(
                    context_key,
                    json.dumps(context),
                    ex=86400 * 7
                )
            
            logger.info(f"Thread created: {thread_id}")
            return thread_id
            
        except Exception as e:
            logger.error(f"Failed to create thread: {e}")
            raise
    
    async def validate_thread(self, thread_id: str) -> bool:
        """
        Validate if thread exists and is active
        
        Args:
            thread_id: Thread identifier
        
        Returns:
            bool: True if thread exists and is active
        """
        try:
            metadata_key = self._get_thread_metadata_key(thread_id)
            metadata_json = await self.redis.get(metadata_key)
            
            if not metadata_json:
                return False
            
            metadata = ThreadMetadata.model_validate_json(metadata_json)
            return metadata.status == ThreadStatus.ACTIVE
            
        except Exception as e:
            logger.error(f"Failed to validate thread {thread_id}: {e}")
            return False
    
    async def execute_task(
        self,
        thread_id: str,
        task: str,
        context_data: Optional[List[dict]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        user_uuid: Optional[str] = None
    ) -> str:
        """
        Execute a task in the specified thread
        
        Args:
            thread_id: Thread identifier
            task: Task description
            context_data: Optional context data
            parameters: Optional task parameters
            user_uuid: Optional user identifier
        
        Returns:
            str: Run ID
        """
        try:
            # Generate run ID
            run_id = generate_uuid()
            
            # Create run record
            thread_run = ThreadRun(
                thread_id=thread_id,
                run_id=run_id,
                status=ThreadRunStatus.PENDING,
                task=task,
                context_data=context_data or [],
                parameters=parameters or {},
                created_at=datetime.utcnow()
            )
            
            # Store run information
            run_key = self._get_thread_run_key(thread_id, run_id)
            await self.redis.set(
                run_key,
                thread_run.model_dump_json(),
                ex=86400  # Expire after 1 day
            )
            
            # Add run to thread's runs list
            runs_key = self._get_thread_runs_key(thread_id)
            await self.redis.lpush(runs_key, run_id)
            await self.redis.ltrim(runs_key, 0, 99)  # Keep last 100 runs
            
            # Update thread metadata
            metadata_key = self._get_thread_metadata_key(thread_id)
            metadata_json = await self.redis.get(metadata_key)
            if metadata_json:
                metadata = ThreadMetadata.model_validate_json(metadata_json)
                metadata.run_count += 1
                metadata.last_run_id = run_id
                metadata.updated_at = datetime.utcnow()
                await self.redis.set(
                    metadata_key,
                    metadata.model_dump_json(),
                    ex=86400 * 7
                )
            
            # Prepare Celery task data with thread support
            task_data = ProcessFlowDataRequest(
                flow_uuid=thread_id,  # Map thread_id to flow_uuid for backward compatibility
                flow_input_uuid=run_id,  # Map run_id to flow_input_uuid for backward compatibility
                user_uuid=user_uuid or "anonymous",
                context_data=context_data or [{"task": task, "parameters": parameters}],
                thread_id=thread_id,  # Explicit thread_id for new thread mode
                run_id=run_id  # Explicit run_id for new thread mode
            )
            
            # Send task to Celery queue
            self.celery_app.send_task(
                'main.process_flow_data',
                args=[task_data.model_dump_json()],
                queue='celery'
            )
            
            # Update run status to processing
            thread_run.status = ThreadRunStatus.PROCESSING
            thread_run.started_at = datetime.utcnow()
            await self.redis.set(
                run_key,
                thread_run.model_dump_json(),
                ex=86400
            )
            
            logger.info(f"Task submitted - thread: {thread_id}, run: {run_id}")
            return run_id
            
        except Exception as e:
            logger.error(f"Failed to execute task in thread {thread_id}: {e}")
            raise
    
    async def get_thread_metadata(self, thread_id: str) -> Optional[ThreadMetadata]:
        """
        Get thread metadata
        
        Args:
            thread_id: Thread identifier
        
        Returns:
            ThreadMetadata or None if not found
        """
        try:
            metadata_key = self._get_thread_metadata_key(thread_id)
            metadata_json = await self.redis.get(metadata_key)
            
            if metadata_json:
                return ThreadMetadata.model_validate_json(metadata_json)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get metadata for thread {thread_id}: {e}")
            return None
    
    async def get_thread_runs(self, thread_id: str, limit: int = 10) -> List[ThreadRun]:
        """
        Get recent runs for a thread
        
        Args:
            thread_id: Thread identifier
            limit: Maximum number of runs to return
        
        Returns:
            List of ThreadRun objects
        """
        try:
            runs_key = self._get_thread_runs_key(thread_id)
            run_ids = await self.redis.lrange(runs_key, 0, limit - 1)
            
            runs = []
            for run_id in run_ids:
                run_key = self._get_thread_run_key(thread_id, run_id)
                run_json = await self.redis.get(run_key)
                if run_json:
                    runs.append(ThreadRun.model_validate_json(run_json))
            
            return runs
            
        except Exception as e:
            logger.error(f"Failed to get runs for thread {thread_id}: {e}")
            return []
    
    async def update_thread_status(self, thread_id: str, status: ThreadStatus) -> bool:
        """
        Update thread status
        
        Args:
            thread_id: Thread identifier
            status: New status
        
        Returns:
            bool: True if successful
        """
        try:
            metadata = await self.get_thread_metadata(thread_id)
            if metadata:
                metadata.status = status
                metadata.updated_at = datetime.utcnow()
                
                metadata_key = self._get_thread_metadata_key(thread_id)
                await self.redis.set(
                    metadata_key,
                    metadata.model_dump_json(),
                    ex=86400 * 7
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update status for thread {thread_id}: {e}")
            return False