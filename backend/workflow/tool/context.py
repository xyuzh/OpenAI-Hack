from typing import Callable, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass

from workflow.service.daytona_sandbox import DaytonaSandbox
from workflow.schema.job_state import JobState

# Avoid circular imports
if TYPE_CHECKING:
    from workflow.runner.runner import Runner


@dataclass
class ToolContext:
    """Context object containing shared state for tool execution"""
    tool_call_uuid: str
    runner: 'Runner'  # Reference to the runner instance
    
    # Properties to maintain backward compatibility
    @property
    def job_dir(self) -> str:
        if self.runner.job_state and self.runner.job_state.job_dir:
            return self.runner.job_state.job_dir
        return ""
    
    @property
    def job_state(self) -> Optional[JobState]:
        return self.runner.job_state
    
    @property
    def daytona(self) -> Optional[DaytonaSandbox]:
        return self.runner.daytona
    
    @daytona.setter
    def daytona(self, value: DaytonaSandbox):
        self.runner.daytona = value
    
    @property
    def on_client_message(self) -> Optional[Callable]:
        return self.runner.on_client_message
    
    @property
    def llm(self) -> Any:
        return self.runner.llm
    
    @property
    def exa(self) -> Any:
        return self.runner.exa
    
    @property
    def agent(self) -> Any:
        return self.runner.agent
    
    @property
    def user(self) -> Any:
        return self.runner.user
    
    @property
    def user_repo(self) -> Any:
        return self.runner.user_repo
    
    @property
    def config(self) -> Any:
        return self.runner.config