from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field
from typing import Optional

_READ_TOOL_DESCRIPTION = """
# Read File Contents

The Read tool reads file contents from the local filesystem and displays them with line numbers in cat -n format.

## Parameters:
- **file_path** (required):Relative path to job directory
- **offset** (optional): Starting line number for large files
- **limit** (optional): Number of lines to read for large files

## Key features:
- Shows line numbers starting at 1
- Reads up to 2000 lines by default
- Truncates lines longer than 2000 characters

## Example usage:
Read with file_path="project_dir/main.py"
Read with file_path="project_dir/config.json" offset=50 limit=100

You must read a file before editing it with the Edit tool.
"""


class FileReadParam(BaseModel):
    file_path: str = Field(..., description="File path relative to the job directory")
    offset: Optional[int] = Field(None, description="Starting line number for large files")
    limit: Optional[int] = Field(None, description="Number of lines to read for large files")


FileReadTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='file_read',
        description=_READ_TOOL_DESCRIPTION,
        parameters=FileReadParam.model_json_schema(),
    ),
)






