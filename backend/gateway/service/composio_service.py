"""
Composio Service for handling authentication and tool execution
"""
import os
import asyncio
from typing import Dict, Any, Optional, List
from composio import Composio
from composio.client.enums import App, Action
from common.utils.logger_utils import get_logger

logger = get_logger(__name__)


class ComposioService:
    """Service for interacting with Composio API"""
    
    def __init__(self):
        """Initialize Composio client with API key from environment"""
        api_key = os.getenv('COMPOSIO_API_KEY')
        if not api_key:
            raise ValueError("COMPOSIO_API_KEY not found in environment variables")
        
        self.client = Composio(api_key=api_key)
        logger.info("Composio service initialized")
    
    async def get_or_create_entity(self, entity_id: str) -> Dict[str, Any]:
        """
        Get or create an entity for the user
        
        Args:
            entity_id: Unique identifier for the user
            
        Returns:
            Entity information
        """
        # For Composio SDK, entities are handled automatically when initiating connections
        # We'll return a simple confirmation
        logger.info(f"Entity {entity_id} will be created automatically when needed")
        return {"entity_id": entity_id, "exists": True}
    
    async def initiate_connection(
        self, 
        entity_id: str, 
        app_name: str
    ) -> Dict[str, Any]:
        """
        Initiate OAuth connection for a specific app
        
        Args:
            entity_id: User's entity ID
            app_name: Name of the app (googledocs, gmail, linear)
            
        Returns:
            Connection information including redirect URL
        """
        try:
            # Map app names to Composio App enum
            app_map = {
                'googledocs': 'GOOGLEDOCS',
                'gmail': 'GMAIL', 
                'jira': 'JIRA'
            }
            
            if app_name.lower() not in app_map:
                raise ValueError(f"Unsupported app: {app_name}")
            
            logger.info(f"Initiating {app_name} connection for user {entity_id}")
            
            # Auth config IDs from Composio dashboard
            # These are the actual IDs for your configured OAuth apps
            auth_config_map = {
                'googledocs': 'ac_XRVlhk6xfkpX',  # Google Docs auth config
                'gmail': 'ac_PcFq3F0MURpp',  # Gmail auth config
                'jira': 'ac_hGPt7ShQobbd'  # Jira auth config
            }
            
            auth_config_id = auth_config_map.get(app_name.lower())
            
            if not auth_config_id:
                # Auth config not found in map
                error_msg = f"Auth config for {app_name} is not configured in the system."
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Initiate the connection
            logger.info(f"Using auth config ID: {auth_config_id}")
            connection = await asyncio.to_thread(
                self.client.connected_accounts.initiate,
                user_id=entity_id,
                auth_config_id=auth_config_id
            )
            
            return {
                "connection_id": getattr(connection, 'id', None),
                "redirect_url": getattr(connection, 'redirect_url', getattr(connection, 'redirectUrl', None)),
                "status": "pending",
                "app": app_name
            }
            
        except Exception as e:
            logger.error(f"Error initiating connection: {e}")
            raise
    
    async def check_connection_status(
        self, 
        entity_id: str,
        app_name: str
    ) -> Dict[str, Any]:
        """
        Check if a connection is active for an app
        
        Args:
            entity_id: User's entity ID
            app_name: Name of the app
            
        Returns:
            Connection status information
        """
        try:
            # Map app names to Composio App enum
            app_map = {
                'googledocs': 'GOOGLEDOCS',
                'gmail': 'GMAIL', 
                'jira': 'JIRA'
            }
            
            app_enum = getattr(App, app_map.get(app_name.lower(), app_name.upper()))
            
            # Get all connected accounts
            connections_response = await asyncio.to_thread(
                self.client.connected_accounts.list
            )
            
            # Convert response to list
            connections = []
            if connections_response:
                if hasattr(connections_response, 'items'):
                    connections = connections_response.items
                elif hasattr(connections_response, '__iter__'):
                    try:
                        connections = list(connections_response)
                    except:
                        connections = []
            
            # Filter connections for this user and app
            user_connections = []
            if connections:
                for conn in connections:
                    # Check user_id from model_extra
                    conn_user_id = None
                    if hasattr(conn, 'model_extra') and conn.model_extra:
                        conn_user_id = conn.model_extra.get('user_id')
                    
                    # Check toolkit slug
                    conn_app = None
                    if hasattr(conn, 'toolkit') and conn.toolkit:
                        conn_app = getattr(conn.toolkit, 'slug', None)
                    
                    # Check if this connection matches our criteria
                    if (conn_user_id == entity_id and 
                        conn_app and conn_app.lower() == app_name.lower() and
                        hasattr(conn, 'status') and conn.status == 'ACTIVE'):
                        user_connections.append(conn)
            
            # Check if we have any active connections
            if user_connections:
                return {
                    "status": "active",
                    "connected": True,
                    "app": app_name
                }
            else:
                return {
                    "status": "not_connected",
                    "connected": False,
                    "app": app_name
                }
                
        except Exception as e:
            logger.error(f"Error checking connection status: {e}")
            return {
                "status": "error",
                "connected": False,
                "app": app_name,
                "error": str(e)
            }
    
    async def search_google_docs(
        self, 
        entity_id: str,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search Google Docs for a user
        
        Args:
            entity_id: User's entity ID
            query: Optional search query
            
        Returns:
            List of Google Docs
        """
        try:
            # Execute the GOOGLEDOCS_SEARCH_DOCUMENTS tool
            logger.info(f"Searching Google Docs for entity {entity_id}")
            
            # Prepare the request
            params = {}
            if query:
                params["query"] = query
            
            # Execute the GOOGLEDOCS_SEARCH_DOCUMENTS tool
            # Note: tools.execute uses 'slug' for the action name
            result = await asyncio.to_thread(
                self.client.tools.execute,
                slug="GOOGLEDOCS_SEARCH_DOCUMENTS",
                arguments=params,
                user_id=entity_id
            )
            
            # Parse and format the response
            if result and 'data' in result:
                documents = result['data'].get('documents', [])
                return self._format_google_docs(documents)
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching Google Docs: {e}")
            raise
    
    def _format_google_docs(self, raw_docs: List[Dict]) -> List[Dict[str, Any]]:
        """
        Format raw Google Docs response to match frontend expectations
        
        Args:
            raw_docs: Raw documents from Composio
            
        Returns:
            Formatted documents list
        """
        formatted_docs = []
        
        for doc in raw_docs:
            # Map Composio response to frontend format
            # Include all fields with None defaults for optional fields
            formatted_doc = {
                "id": doc.get("id", ""),
                "name": doc.get("name", doc.get("title", "")),
                "mimeType": doc.get("mimeType", "application/vnd.google-apps.document"),
                "createdTime": doc.get("createdTime", ""),
                "modifiedTime": doc.get("modifiedTime", None),
                "webViewLink": doc.get("webViewLink", None),
                "size": str(doc.get("size", 0)),
                "starred": doc.get("starred", False),
                "trashed": doc.get("trashed", False),
                "shared": doc.get("shared", False),
                "owners": None,  # Will be set below if available
                "lastModifyingUser": None,  # Will be set below if available
                "permissions": None,  # Will be set below if available
            }
            
            # Add owner information if available
            if "owners" in doc and doc["owners"]:
                formatted_doc["owners"] = [
                    {
                        "displayName": owner.get("displayName", ""),
                        "emailAddress": owner.get("emailAddress", ""),
                        "photoLink": owner.get("photoLink", ""),
                        "kind": "drive#user"
                    }
                    for owner in doc["owners"]
                ]
            
            # Add last modifying user if available
            if "lastModifyingUser" in doc:
                user = doc["lastModifyingUser"]
                formatted_doc["lastModifyingUser"] = {
                    "displayName": user.get("displayName", ""),
                    "emailAddress": user.get("emailAddress", ""),
                    "photoLink": user.get("photoLink", ""),
                    "kind": "drive#user"
                }
            
            # Add permissions if available
            if "permissions" in doc and doc["permissions"]:
                formatted_doc["permissions"] = doc["permissions"]
            
            formatted_docs.append(formatted_doc)
        
        return formatted_docs
    
    async def get_document_by_id(
        self,
        entity_id: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Fetch a specific Google Doc by its ID
        
        Args:
            entity_id: User's entity ID
            document_id: Google Doc ID
            
        Returns:
            Document content and metadata
        """
        try:
            logger.info(f"Fetching Google Doc {document_id} for entity {entity_id}")
            
            # Execute GOOGLEDOCS_GET_DOCUMENT action
            result = await asyncio.to_thread(
                self.client.tools.execute,
                slug="GOOGLEDOCS_GET_DOCUMENT",
                arguments={"documentId": document_id},
                user_id=entity_id
            )
            
            # Parse the document content
            if result and 'data' in result:
                doc_data = result['data']
                
                # Extract text content from the document structure
                content = self._extract_document_text(doc_data)
                
                return {
                    "document_id": document_id,
                    "title": doc_data.get("title", "Untitled"),
                    "content": content,
                    "body": doc_data.get("body", {}),
                    "raw_data": doc_data
                }
            
            return {
                "document_id": document_id,
                "title": "Unknown",
                "content": "",
                "error": "No data returned"
            }
            
        except Exception as e:
            logger.error(f"Error fetching document {document_id}: {e}")
            raise
    
    def _extract_document_text(self, doc_data: Dict) -> str:
        """
        Extract plain text content from Google Docs API response
        
        Args:
            doc_data: Document data from Google Docs API
            
        Returns:
            Plain text content
        """
        content_parts = []
        
        # Check for direct text field first
        if "text" in doc_data:
            return doc_data["text"]
        
        # Otherwise, extract from body structure
        body = doc_data.get("body", {})
        if body:
            content_elements = body.get("content", [])
            for element in content_elements:
                if "paragraph" in element:
                    paragraph = element["paragraph"]
                    para_elements = paragraph.get("elements", [])
                    for para_elem in para_elements:
                        if "textRun" in para_elem:
                            text = para_elem["textRun"].get("content", "")
                            content_parts.append(text)
                            
                elif "sectionBreak" in element:
                    content_parts.append("\n\n")
        
        return "".join(content_parts)
    
    async def execute_tool(
        self,
        entity_id: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a generic Composio tool
        
        Args:
            entity_id: User's entity ID
            tool_name: Name of the tool to execute
            params: Optional parameters for the tool
            
        Returns:
            Tool execution result
        """
        try:
            logger.info(f"Executing tool {tool_name} for entity {entity_id}")
            
            # Execute the tool using the slug
            result = await asyncio.to_thread(
                self.client.tools.execute,
                slug=tool_name,
                arguments=params or {},
                user_id=entity_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            raise


# Singleton instance
_composio_service: Optional[ComposioService] = None


def get_composio_service() -> ComposioService:
    """Get or create the Composio service singleton"""
    global _composio_service
    if _composio_service is None:
        _composio_service = ComposioService()
    return _composio_service