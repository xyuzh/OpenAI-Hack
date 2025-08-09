from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field

_FILE_CREATION_DESCRIPTION = """
The Write tool creates new files or completely overwrites existing files with provided content.

Key requirements:
- Must use Read first if file already exists
- Completely overwrites existing file content
- NEVER proactively create documentation files (*.md, README)

Use sparingly - editing existing files is preferred over writing new ones.
"""

class FileWriteParam(BaseModel):
    file_path: str = Field(..., description="File path relative to the job directory")
    content: str = Field(..., description="Complete content to write to the file")

FilesCreationTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='file_write',
        description=_FILE_CREATION_DESCRIPTION,
        parameters=FileWriteParam.model_json_schema(),
    ),
)