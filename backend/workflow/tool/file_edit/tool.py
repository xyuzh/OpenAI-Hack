from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field
from typing import List

_FILE_EDIT_DESCRIPTION = """
The Edit tool performs exact string replacements in a file. You must read the file first before editing.

Key requirements:
- Must use Read tool first before editing
- old_string must match file contents exactly (including whitespace/indentation)
- Preserve exact indentation from Read output (ignore line number prefixes)
- Edit fails if old_string isn't unique unless using replace_all
"""


class FileEditParam(BaseModel):
    old_str: str = Field(
        ...,
        description="The exact string to replace from the file. Must match completely including all whitespace, indentation, and line breaks. Should include enough context to ensure it matches exactly one location in the file.",
    )
    new_str: str = Field(
        ..., description="The new string to insert in place of the old string"
    )
    path: str = Field(..., description="File path relative to the job directory")



FileEditTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='file_edit',
        description=_FILE_EDIT_DESCRIPTION,
        parameters=FileEditParam.model_json_schema(),
    ),
)
