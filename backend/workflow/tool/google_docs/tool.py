from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field
from typing import Optional


_GOOGLE_DOCS_DESCRIPTION = """
This tool fetches the content of a Google Doc using its document ID.
It retrieves the full document content including text, formatting, and structure.
"""


class GoogleDocsParam(BaseModel):
    document_id: str = Field(description="The Google Doc ID to fetch")
    entity_id: str = Field(description="The user entity ID for Composio authentication")
    include_formatting: bool = Field(
        default=False,
        description="Whether to include formatting information in the response"
    )


GoogleDocsTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='google_docs_fetch',
        description=_GOOGLE_DOCS_DESCRIPTION,
        parameters=GoogleDocsParam.model_json_schema(),
    ),
)