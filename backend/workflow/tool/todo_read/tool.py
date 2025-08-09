from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel

_TODO_READ_DESCRIPTION = """
TodoRead returns the current todo items with status, priority, and content.

No parameters required - returns current todo list from job state.
Use frequently to track progress and plan next steps.
"""


class TodoReadParam(BaseModel):
    """No parameters needed for TodoRead"""
    pass


TodoReadTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='todo_read',
        description=_TODO_READ_DESCRIPTION,
        parameters=TodoReadParam.model_json_schema(),
    ),
)