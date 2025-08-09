from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field
from enum import Enum

_WEB_SEARCH_DESCRIPTION = """
This tool enables web search in two ways:
- url
- natural language query
"""

class WebSearchType(Enum):
    SEARCH = "search"
    CRAWL = "url_crawl"

class WebSearchParam(BaseModel):
    query: str = Field(description="url or search query")
    type: WebSearchType = Field(description="The type of search to perform")


WebSearchTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='web_search',
        description=_WEB_SEARCH_DESCRIPTION,
        parameters=WebSearchParam.model_json_schema(),
    ),
)
