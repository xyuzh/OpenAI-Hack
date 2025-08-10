from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List, Dict, Any


_JIRA_TOOL_DESCRIPTION = """
This tool enables interaction with Jira to create and manage issues.
The tool will automatically handle authentication and API calls through Composio.
Provide natural language instructions and the tool will execute the appropriate Jira actions.
"""


class JiraActionType(Enum):
    CREATE_ISSUE = "create_issue"
    UPDATE_ISSUE = "update_issue"
    ADD_COMMENT = "add_comment"
    GET_ISSUE = "get_issue"
    SEARCH_ISSUES = "search_issues"


class JiraParam(BaseModel):
    action: JiraActionType = Field(description="The type of Jira action to perform")
    instructions: str = Field(
        description="Natural language instructions for what to do in Jira. "
        "For CREATE_ISSUE: describe the issue title, description, type, priority, etc. "
        "For UPDATE_ISSUE: specify issue key and what to update. "
        "For ADD_COMMENT: specify issue key and comment text."
    )
    entity_id: str = Field(description="The user entity ID for Composio authentication")
    project_key: Optional[str] = Field(
        default=None, 
        description="Jira project key (e.g., 'PROJ'). If not provided, will use default project."
    )
    issue_key: Optional[str] = Field(
        default=None,
        description="Jira issue key (e.g., 'PROJ-123') for update/comment actions"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata for the action"
    )


JiraTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='jira_tool',
        description=_JIRA_TOOL_DESCRIPTION,
        parameters=JiraParam.model_json_schema(),
    ),
)