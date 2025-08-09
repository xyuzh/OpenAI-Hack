from pydantic import BaseModel, Field
from typing import Optional
from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

_GREP_TOOL_DESCRIPTION = """
# Grep Pattern Search

The grep tool searches for text patterns in files using regular expressions.

## Usage notes:
- Use for finding files containing specific patterns
- For counting matches within files, use Bash with rg instead
- For open-ended searches needing multiple rounds, use Task tool
- Can batch multiple searches in single response
  
## Example usage:
  pattern: "handleSubmit"
  include: "*.tsx"
  path: "src/components"

Use this tool when you need to search for specific text patterns across files.
"""


class GrepToolParam(BaseModel):
    pattern: str = Field(..., description="Regular expression to search for")
    path: Optional[str] = Field(None, description="Directory to search in (defaults to current directory)")
    include: Optional[str] = Field(None, description='File pattern filter (e.g., "*.js", "*.{ts,tsx}")')


GrepTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='grep_tool',
        description=_GREP_TOOL_DESCRIPTION,
        parameters=GrepToolParam.model_json_schema(),
    ),
)
