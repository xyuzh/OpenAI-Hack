from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field
from typing import List, Optional

_MULTI_EDIT_DESCRIPTION = """
The MultiEdit tool performs multiple find-and-replace operations on a single file in one atomic operation.

Key features:
- All edits applied sequentially in order provided
- Atomic operation - either all edits succeed or none are applied
- Each edit operates on the result of the previous edit
- Must read file first before editing
- Same exact matching requirements as Edit tool

Ideal for making several related changes to the same file efficiently.
"""


class EditOperation(BaseModel):
    old_string: str = Field(
        ...,
        description="Exact text to replace. Must match completely including all whitespace, indentation, and line breaks."
    )
    new_string: str = Field(
        ...,
        description="Replacement text"
    )
    replace_all: bool = Field(
        default=False,
        description="Replace all occurrences if true, otherwise replace only the first occurrence"
    )


class MultiEditParam(BaseModel):
    file_path: str = Field(
        ...,
        description="Relative to job directory"
    )
    edits: List[EditOperation] = Field(
        ...,
        description="Array of edit operations to apply sequentially"
    )


MultiEditTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='multi_edit',
        description=_MULTI_EDIT_DESCRIPTION,
        parameters=MultiEditParam.model_json_schema(),
    ),
)
