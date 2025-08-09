from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field

_URL_EXPOSE_TOOL_DESCRIPTION = """
Call this tool AFTER successfully starting a local server or web application to expose the accessible URL to the user. 
This tool should be used when you've launched an app locally
and need to provide the user with the URL they can visit to access the running application in their browser.
Only call this tool once the server is confirmed to be running and listening on the specified port.
"""


class UrlExposeParam(BaseModel):
    port: int = Field(..., description="The port number where the application is currently running and accepting connections")
    app_folder: str = Field(..., description="The folder name of the app")


UrlExposeTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='expose_app_url',
        description=_URL_EXPOSE_TOOL_DESCRIPTION,
        parameters=UrlExposeParam.model_json_schema(),
    ),
)