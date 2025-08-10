from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


class ThreadStatus(str, Enum):
    """Thread status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ThreadRunStatus(str, Enum):
    """Thread run status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ThreadInitRequest(BaseModel):
    """Request model for thread initialization"""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ThreadInitResponse(BaseModel):
    """Response model for thread initialization"""
    thread_id: str
    created_at: str
    status: ThreadStatus = ThreadStatus.ACTIVE


class ThreadExecuteRequest(BaseModel):
    """Request model for thread task execution"""
    task: str
    context_data: Optional[List[dict]] = Field(default_factory=list)
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    user_uuid: Optional[str] = None
    document_id: Optional[str] = Field(default=None, description="Google Doc ID to process")
    entity_id: Optional[str] = Field(default="default-user", description="User entity ID for Composio")


class ThreadExecuteResponse(BaseModel):
    """Response model for thread task execution"""
    thread_id: str
    run_id: str
    status: ThreadRunStatus
    created_at: str


class ThreadMetadata(BaseModel):
    """Thread metadata stored in Redis"""
    thread_id: str
    status: ThreadStatus
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    run_count: int = 0
    last_run_id: Optional[str] = None


class ThreadRun(BaseModel):
    """Individual thread run information"""
    thread_id: str
    run_id: str
    status: ThreadRunStatus
    task: str
    context_data: List[dict] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None