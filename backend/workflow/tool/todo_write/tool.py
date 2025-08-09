from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field
from typing import List
from workflow.schema.job_state import Todo

_TODO_WRITE_DESCRIPTION = """
TodoWrite manages structured task lists for coding sessions.

Updates the todo list with new tasks or status changes.
Only include tasks that are new or have changed status - don't' include already existent todos that remain unchanged.
Only ONE task should be "in_progress" at a time.
Mark tasks completed immediately after finishing.
"""


class TodoWriteParam(BaseModel):
    todos: List[Todo] = Field(
        ...,
        description="Array of todo objects with id, content, status (pending/in_progress/completed), and priority (high/medium/low)"
    )


TodoWriteTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='todo_write',
        description=_TODO_WRITE_DESCRIPTION,
        parameters=TodoWriteParam.model_json_schema(),
    ),
) 