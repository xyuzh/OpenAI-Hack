from pydantic import BaseModel, Field


from typing import Optional

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

_BASH_TOOL_DESCRIPTION = """
Execute shell commands in an Ubuntu 22.04 environment.

**Available Package Managers:**
- Python: Use `uv` for packages and virtual environments
- JavaScript/TypeScript: Use `bun` for packages, execution, and builds
- System: Use `apt` for system packages

**Tips:**
- Commands execute in the current working directory (use `cwd` to change)
- For long-running processes (servers, watchers), set `is_long_running=True`
- Use relative paths for file operations
"""


class BashToolParam(BaseModel):
    cmd: str = Field(..., description="The command to run")
    timeout: Optional[int] = Field(
        None,
        description="Timeout in seconds (default: no timeout)",
    )
    env: Optional[dict[str, str]] = Field(
        None,
        description="Environment variables to set",
    )
    is_long_running: Optional[bool] = Field(
        False,
        description="True for long-running processes (servers, watchers) to prevent timeouts",
    )
    cwd: Optional[str] = Field(
        None,
        description="Working directory (default: job directory)",
    )


BashTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='bash_tool',
        description=_BASH_TOOL_DESCRIPTION,
        parameters=BashToolParam.model_json_schema(),
    ),
)
