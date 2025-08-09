from abc import ABC, abstractmethod
from typing import Optional, List
from pydantic import BaseModel, Field

from workflow.service.schema import BashOps
from workflow.schema.user import User


class FileItem(BaseModel):
    path: str = Field(description="File path")
    content: str = Field(description="The content of the file, must be string")


class SandboxBase(ABC):
    """Abstract base class for sandbox implementations"""
    
    @abstractmethod
    async def upload_files(self, files: List[FileItem]) -> None:
        """Upload files to the sandbox"""
        pass
    
    @abstractmethod
    async def download_files(self, files_path: List[str]) -> List[FileItem]:
        """Download files from the sandbox"""
        pass
    
    @abstractmethod
    async def run_bash(self, bash_ops: BashOps, cwd: str) -> str:
        """Run a bash command in the sandbox"""
        pass
    
    @abstractmethod
    async def run_bash_async(self, cmd: str, cwd: str, session_id: str = '') -> str:
        """Run a bash command asynchronously in the sandbox
        
        Default implementation just calls run_bash. Subclasses can override
        this for true async execution if supported.
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close/cleanup the sandbox resources"""
        pass 