from pydantic import BaseModel, Field
from typing import Optional
from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

_GLOB_TOOL_DESCRIPTION = """
# Glob Pattern File Search

The Glob tool performs fast file pattern matching using glob patterns to find files by
name/path patterns.

## Parameters:
- **pattern** (required): The glob pattern to match files against
- **path** (optional): Directory to search in (defaults to current working directory)

## Common patterns:
- `**/*.js` - All JavaScript files recursively
- `src/**/*.ts` - All TypeScript files in src/ and subdirectories
- `*.json` - All JSON files in current directory
- `**/test*.py` - All Python test files recursively
- `components/**/*.{tsx,jsx}` - All React component files

## Features:
- Works with any codebase size
- Returns file paths sorted by modification time
- Faster than using bash find commands
- Supports standard glob syntax with wildcards

## Example usage:
Glob with pattern: "**/*.py" 
# Returns all Python files in project
"""


class GlobToolParam(BaseModel):
    pattern: str = Field(..., description="The glob pattern to match files against")
    path: Optional[str] = Field(
        None,
        description="Directory to search in (defaults to current working directory)"
    )


GlobTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='glob_tool',
        description=_GLOB_TOOL_DESCRIPTION,
        parameters=GlobToolParam.model_json_schema(),
    ),
)
