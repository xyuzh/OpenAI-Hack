import os
from enum import Enum
from typing import Literal
import uuid
from datetime import datetime, timezone
from dataclasses import asdict
from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional

from workflow.agent.tool.plan_task import JobPlan
from workflow.core.message import Message


class JobRunState(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PENDING = "pending"
    FAILED = "failed"


class Todo(BaseModel):
    id: str = Field(description="Unique identifier")
    content: str = Field(description="Task description")
    status: Literal['pending', 'in_progress', 'completed']
    priority: Literal['low', 'medium', 'high']

class JobState(BaseModel):
    id: str
    job_plan: JobPlan | None = Field(default=None)
    state: JobRunState = Field(default=JobRunState.NOT_STARTED)
    messages: list[Message] = Field(default_factory=list)
    time_created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    todo_list: list[Todo] = Field(default_factory=list)

    @property
    def job_dir(self) -> str | None:
        if self.job_plan is None:
            return None
        return os.path.join(
            '/workspace',
            self.job_plan.name + '_' + self.time_created.strftime('%y%m%d%H%M'),
        )

    def to_dict(self):
        return asdict(self)
