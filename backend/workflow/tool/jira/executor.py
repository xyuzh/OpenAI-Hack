import asyncio
import json
from typing import Any, Dict, Optional
from openai import AsyncOpenAI
from composio import Composio
from pydantic import BaseModel

from common.utils.logger_utils import get_logger
from common.type.agent import AgentExecuteType
from workflow.tool.base import BaseTool
from workflow.tool.context import ToolContext
from workflow.tool.jira.tool import JiraTool, JiraParam, JiraActionType

logger = get_logger(__name__)


class JiraToolExecutor(BaseTool):
    """Executor for Jira tool operations using Composio"""
    
    name = "jira_tool"
    param_class = JiraParam
    tool_definition = JiraTool
    execute_type = AgentExecuteType.JIRA_ACTION
    
    def __init__(self):
        super().__init__()
        self.composio_client = None
        self.openai_client = None
        
    async def _initialize_clients(self):
        """Initialize Composio and OpenAI clients"""
        if not self.composio_client:
            import os
            api_key = os.getenv('COMPOSIO_API_KEY')
            if not api_key:
                raise ValueError("COMPOSIO_API_KEY not found in environment")
            self.composio_client = Composio(api_key=api_key)
            
        if not self.openai_client:
            import os
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self.openai_client = AsyncOpenAI(api_key=api_key)
    
    async def execute(self, params: JiraParam, context: ToolContext) -> Any:
        """
        Execute Jira action using Composio
        
        Args:
            params: JiraParam with action details
            context: Tool execution context
            
        Returns:
            Result of the Jira action
        """
        await self._initialize_clients()
        
        logger.info(f"Executing Jira action: {params.action.value}")
        
        # Send init message
        await self.send_init_message(
            context,
            execute_params={
                "action": params.action.value,
                "entity_id": params.entity_id,
                "project_key": params.project_key,
                "issue_key": params.issue_key
            }
        )
        
        try:
            # Check if Jira is connected for this user
            logger.info(f"Checking Jira connection for entity: {params.entity_id}")
            
            connections = await asyncio.to_thread(
                self.composio_client.connected_accounts.list
            )
            
            # Filter for this user's Jira connection
            jira_connected = False
            if connections:
                for conn in connections:
                    conn_user_id = None
                    conn_app = None
                    
                    if hasattr(conn, 'model_extra') and conn.model_extra:
                        conn_user_id = conn.model_extra.get('user_id')
                    if hasattr(conn, 'toolkit') and conn.toolkit:
                        conn_app = getattr(conn.toolkit, 'slug', None)
                    
                    if (conn_user_id == params.entity_id and 
                        conn_app and conn_app.lower() == 'jira' and
                        hasattr(conn, 'status') and conn.status == 'ACTIVE'):
                        jira_connected = True
                        break
            
            if not jira_connected:
                error_msg = f"Jira is not connected for user {params.entity_id}. Please connect Jira first."
                logger.error(error_msg)
                await context.on_client_message_text(error_msg)
                return {"error": error_msg}
            
            # Map action type to Composio tool
            tool_mapping = {
                JiraActionType.CREATE_ISSUE: "JIRA_CREATE_ISSUE",
                JiraActionType.UPDATE_ISSUE: "JIRA_UPDATE_ISSUE", 
                JiraActionType.ADD_COMMENT: "JIRA_ADD_COMMENT_TO_ISSUE",
                JiraActionType.GET_ISSUE: "JIRA_GET_ISSUE",
                JiraActionType.SEARCH_ISSUES: "JIRA_SEARCH_ISSUES"
            }
            
            tool_name = tool_mapping.get(params.action)
            if not tool_name:
                raise ValueError(f"Unsupported Jira action: {params.action}")
            
            # Get the specific Jira tool
            logger.info(f"Getting Jira tool: {tool_name}")
            tools = await asyncio.to_thread(
                self.composio_client.tools.get,
                user_id=params.entity_id,
                tools=[tool_name]
            )
            
            # Prepare the prompt based on action type
            system_prompt = "You are a helpful assistant that manages Jira issues."
            user_prompt = self._build_user_prompt(params)
            
            # Send status update
            await context.on_client_message_text(f"Processing Jira {params.action.value}...")
            
            # Call OpenAI to generate tool call
            logger.info("Calling OpenAI to generate Jira action")
            response = await self.openai_client.chat.completions.create(
                model="gpt-5",
                tools=tools,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Execute the tool calls via Composio
            logger.info("Executing Jira action via Composio")
            result = await asyncio.to_thread(
                self.composio_client.provider.handle_tool_calls,
                response=response,
                user_id=params.entity_id
            )
            
            # Parse and format the result
            formatted_result = self._format_result(params.action, result)
            
            # Send success message
            success_msg = self._build_success_message(params.action, formatted_result)
            await context.on_client_message_text(success_msg)
            
            # Send complete message
            await self.send_complete_message(
                context,
                execute_result=formatted_result
            )
            
            return formatted_result
            
        except Exception as e:
            error_msg = f"Failed to execute Jira action: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await context.on_client_message_text(error_msg)
            
            await self.send_complete_message(
                context,
                execute_result={"error": error_msg}
            )
            
            return {"error": error_msg}
    
    def _build_user_prompt(self, params: JiraParam) -> str:
        """Build user prompt based on action type"""
        base_prompt = params.instructions
        
        if params.action == JiraActionType.CREATE_ISSUE:
            if params.project_key:
                base_prompt += f"\n\nUse project key: {params.project_key}"
            base_prompt += "\n\nCreate this as a Jira issue with appropriate issue type (Task, Bug, Story, etc.) and priority."
            
        elif params.action == JiraActionType.UPDATE_ISSUE:
            if params.issue_key:
                base_prompt = f"Update issue {params.issue_key}: {base_prompt}"
                
        elif params.action == JiraActionType.ADD_COMMENT:
            if params.issue_key:
                base_prompt = f"Add this comment to issue {params.issue_key}: {base_prompt}"
                
        elif params.action == JiraActionType.GET_ISSUE:
            if params.issue_key:
                base_prompt = f"Get details for issue {params.issue_key}"
            else:
                base_prompt = f"Get issue details: {base_prompt}"
                
        elif params.action == JiraActionType.SEARCH_ISSUES:
            base_prompt = f"Search for issues: {base_prompt}"
            
        return base_prompt
    
    def _format_result(self, action: JiraActionType, result: Any) -> Dict[str, Any]:
        """Format the result based on action type"""
        if not result:
            return {"status": "completed", "data": None}
            
        # Extract relevant information based on action
        if action == JiraActionType.CREATE_ISSUE:
            # Try to extract issue key and URL from result
            if isinstance(result, dict):
                return {
                    "status": "created",
                    "issue_key": result.get("key", "Unknown"),
                    "issue_id": result.get("id"),
                    "self_url": result.get("self"),
                    "web_url": self._build_web_url(result.get("key"))
                }
            elif isinstance(result, list) and result:
                # Sometimes result is a list of responses
                first_result = result[0] if isinstance(result[0], dict) else {}
                return {
                    "status": "created",
                    "issue_key": first_result.get("key", "Unknown"),
                    "data": first_result
                }
                
        return {
            "status": "completed",
            "action": action.value,
            "data": result
        }
    
    def _build_web_url(self, issue_key: Optional[str]) -> Optional[str]:
        """Build Jira web URL for an issue"""
        if not issue_key:
            return None
        # This is a placeholder - in production, you'd get the Jira instance URL from config
        # For now, return a template
        return f"https://your-domain.atlassian.net/browse/{issue_key}"
    
    def _build_success_message(self, action: JiraActionType, result: Dict[str, Any]) -> str:
        """Build a success message based on action and result"""
        if action == JiraActionType.CREATE_ISSUE:
            issue_key = result.get("issue_key", "Unknown")
            web_url = result.get("web_url")
            msg = f"✅ Successfully created Jira issue: {issue_key}"
            if web_url:
                msg += f"\n🔗 View issue: {web_url}"
            return msg
            
        elif action == JiraActionType.UPDATE_ISSUE:
            return f"✅ Successfully updated Jira issue"
            
        elif action == JiraActionType.ADD_COMMENT:
            return f"✅ Successfully added comment to Jira issue"
            
        elif action == JiraActionType.GET_ISSUE:
            return f"✅ Successfully retrieved Jira issue details"
            
        elif action == JiraActionType.SEARCH_ISSUES:
            data = result.get("data", [])
            count = len(data) if isinstance(data, list) else 0
            return f"✅ Found {count} Jira issue(s)"
            
        return f"✅ Jira action completed successfully"