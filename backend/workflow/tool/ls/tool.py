from pydantic import BaseModel, Field
from typing import Optional, List
from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

_LS_TOOL_DESCRIPTION = """
# List Directory Contents

The LS tool lists files and directories in a specified path. It requires a relative path and optionally
accepts glob patterns to ignore certain files or directories.

**IMPORTANT**: ignore `node_modules` for web app.
## Example usage:
- `LS with path="project/src"`
- `LS with path="project" and ignore=["*.log", "node_modules"]`

Use this when you need to see directory contents before performing other operations.
"""


class LsToolParam(BaseModel):
    path: str = Field(..., description="Relative path to job directory")
    ignore: Optional[List[str]] = Field(
        None,
        description="Array of glob patterns to exclude from results"
    )


LsTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='ls_tool',
        description=_LS_TOOL_DESCRIPTION,
        parameters=LsToolParam.model_json_schema(),
    ),
)
