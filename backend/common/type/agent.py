from __future__ import annotations

from enum import Enum
from typing import Optional, Any, List, Literal, TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

from common.type.constant import CurrentState
from common.utils.string_utils import validate_uuid_format
from workflow.agent.tool.plan_task import JobPlan

# Avoid circular imports - these imports are only used for type hints
if TYPE_CHECKING:
    from workflow.tool.use_template.tool import UseTemplateParam
    from workflow.tool.file_write.tool import FileWriteParam
    from workflow.tool.file_edit.tool import FileEditParam
    from workflow.tool.multi_edit.tool import MultiEditParam, EditOperation
    from workflow.tool.todo_write.tool import TodoWriteParam
    from workflow.schema.job_state import Todo


class WorkflowConfig(BaseModel):
    """用于模型调用时，传递的配置"""

    api_key: str = Field(..., description="API Key")
    model: str = Field(..., description="Model Name")


class WebCrawlResult(BaseModel):
    """WebCrawl工具执行结果"""

    url: str = Field(description="网页URL")
    content: str = Field(description="网页内容")


class WebSearchResult(BaseModel):
    """WebSearch工具执行结果"""

    url: str = Field(description="网页URL")
    title: str = Field(description="网页标题")
    content: str = Field(description="网页内容")


class AppCreateViteResult(BaseModel):
    """AppCreateVite工具执行结果"""

    url: str = Field(description="应用URL")
    sandbox_id: str = Field(description="沙盒ID")


class AgentExecuteType(str, Enum):
    # TODO 可以改这里所有的变量的名称、类型、数量
    ASSISTANT_RESPONSE = "assistant_response"
    # 工具JobPlan
    TOOL_JOB_PLAN = "tool_job_plan"
    TOOL_USE_TEMPLATE = "tool_use_template"
    TOOL_FILE_VIEW = "tool_file_view"
    TOOL_FILE_READ = "tool_file_read"
    TOOL_FILE_EDIT = "tool_file_edit"
    TOOL_MULTI_EDIT = "tool_multi_edit"
    TOOL_TODO_READ = "tool_todo_read"
    TOOL_TODO_WRITE = "tool_todo_write"
    TOOL_BASH = "tool_bash"
    TOOL_FILES_CREATION = "tool_files_creation"
    TOOL_FILES_VIEW = "tool_files_view"
    TOOL_FILES_EDIT = "tool_files_edit"
    TOOL_SUGGEST_NEXT_STEPS = "tool_suggest_next_steps"
    TOOL_GLOB = "tool_glob"
    TOOL_LS = "tool_ls"
    TOOL_GREP = "tool_grep"
    FLOW_COMPLETION = "flow_completion"
    STATUS_SANDBOX_INFO = "status_sandbox_info"


class ToolBashResult(BaseModel):
    """Bash工具执行结果"""
    cmd: str = Field(..., description="Bash操作")
    cwd: str = Field(description="当前工作目录")
    result: Optional[str] = Field(default=None, description="Bash执行结果")

class GlobToolResult(BaseModel):
    """Glob工具执行结果"""
    pattern: str = Field(..., description="Glob模式")
    path: Optional[str] = Field(default=None, description="搜索路径")
    result: Optional[str] = Field(default=None, description="Glob执行结果")

class LsToolResult(BaseModel):
    """Ls工具执行结果"""
    path: str = Field(..., description="目录路径")
    ignore: Optional[List[str]] = Field(default=None, description="忽略的模式列表")
    result: Optional[str] = Field(default=None, description="Ls执行结果")

class GrepToolResult(BaseModel):
    """Grep工具执行结果"""
    pattern: str = Field(..., description="搜索模式")
    path: str = Field(..., description="搜索路径")
    result: Optional[str] = Field(default=None, description="Grep执行结果")

class FileReadResult(BaseModel):
    """FileRead工具执行结果"""
    file_path: str = Field(..., description="文件路径")
    content: Optional[str] = Field(default=None, description="文件内容")


class SandboxInfo(BaseModel):
    """沙盒信息"""
    sandbox_id: str = Field(..., description="沙盒ID")
    sandbox_url: str = Field(..., description="沙盒URL")
    app_path: str = Field(..., description="应用路径")


class AgentExecuteResult(BaseModel):
    """Agent执行结果"""
    assistant_response_result: Optional[str] = Field(
        default=None, description="AssistantResponse"
    )
    tool_job_plan_result: Optional[JobPlan] = Field(
        default=None, description="JobPlan工具执行结果"
    )
    tool_bash_result: Optional[ToolBashResult] = Field(
        default=None, description="Bash工具执行结果"
    )
    tool_file_write_result: Optional[FileWriteParam] = Field(
        default=None, description="FilesCreation工具执行结果"
    )
    tool_use_template_result: Optional[UseTemplateParam] = Field(
        default=None, description="UseTemplate工具执行结果"
    )

    tool_file_edit_result: Optional[FileEditParam] = Field(
        default=None, description="FilesEdit工具执行结果"
    )
    tool_multi_edit_result: Optional[MultiEditParam] = Field(
        default=None, description="MultiEdit工具执行结果"
    )
    tool_todo_read_result: Optional[TodoWriteParam] = Field(
        default=None, description="TodoRead工具执行结果"
    )
    tool_todo_write_result: Optional[TodoWriteParam] = Field(
        default=None, description="TodoWrite工具执行结果"
    )
    tool_suggest_next_steps_result: Optional[list[str]] = Field(
        default=None, description="SuggestNextSteps工具执行结果"
    )
    status_sandbox_info: Optional[SandboxInfo] = Field(
        default=None, description="JobFinish工具执行结果"
    )
    flow_completion_message: Optional[str] = Field(
        default=None, description="FlowCompletion消息"
    )
    tool_glob_result: Optional[GlobToolResult] = Field(
        default=None, description="Glob工具执行结果"
    )
    tool_ls_result: Optional[LsToolResult] = Field(
        default=None, description="Ls工具执行结果"
    )
    tool_grep_result: Optional[GrepToolResult] = Field(
        default=None, description="Grep工具执行结果"
    )
    tool_file_read_result: Optional[FileReadResult] = Field(
        default=None, description="FileRead工具执行结果"
    )


class AgentExecuteData(BaseModel):
    # TODO 这里的数据结构不能改
    """AgentFlow事件流数据"""
    uuid: str = Field(description="UUID")
    create_at: Optional[str] = Field(default=None, description="创建时间，注意这里的值发给后端之后，后端会在onCreate函数中对值进行更新")
    modify_at: Optional[str] = Field(default=None, description="修改时间，注意这里的值发给后端之后，后端会在onCreate、onModify函数中对值进行更新")
    current_state: CurrentState = Field(description="当前状态")
    execute_start_at: Optional[str] = Field(default=None, description="执行开始时间")
    execute_end_at: Optional[str] = Field(default=None, description="执行结束时间")
    error_flag: bool = Field(description="错误标志")
    execute_type: AgentExecuteType = Field(description="执行类型")
    execute_result: Optional[AgentExecuteResult] = Field(
        default=None, description="执行结果"
    )

    @field_validator('uuid')
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        """验证UUID格式"""
        return validate_uuid_format(v)


# Try to rebuild models with actual types when this module is imported
# This handles the case where the workflow modules are already available
try:
    from workflow.tool.use_template.tool import UseTemplateParam
    from workflow.tool.file_write.tool import FileWriteParam
    from workflow.tool.file_edit.tool import FileEditParam
    from workflow.tool.multi_edit.tool import MultiEditParam
    from workflow.tool.todo_write.tool import TodoWriteParam
    
    # If imports succeed, rebuild the models immediately
    AgentExecuteResult.model_rebuild()
    AgentExecuteData.model_rebuild()
except ImportError:
    # If imports fail (circular import), we'll rebuild later
    # The rebuild_models() function can be called manually if needed
    pass


# Function to rebuild models with actual types
def rebuild_models():
    """
    This function should be called after all the workflow tool modules are imported
    to resolve the forward references in the models.
    """
    # Import the actual types into the current namespace
    from workflow.tool.use_template.tool import UseTemplateParam
    from workflow.tool.file_write.tool import FileWriteParam
    from workflow.tool.file_edit.tool import FileEditParam
    from workflow.tool.multi_edit.tool import MultiEditParam
    from workflow.tool.todo_write.tool import TodoWriteParam
    
    # Make types available in the module's global namespace
    globals()['UseTemplateParam'] = UseTemplateParam
    globals()['FileWriteParam'] = FileWriteParam
    globals()['FileEditParam'] = FileEditParam
    globals()['MultiEditParam'] = MultiEditParam
    globals()['TodoWriteParam'] = TodoWriteParam
    
    # Rebuild the models - they will now find the types in the global namespace
    AgentExecuteResult.model_rebuild()
    AgentExecuteData.model_rebuild()
