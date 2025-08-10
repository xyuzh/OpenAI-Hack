import asyncio
from typing import Any, Dict
from composio import Composio
from pydantic import BaseModel

from common.utils.logger_utils import get_logger
from common.type.agent import AgentExecuteType
from workflow.tool.base import BaseTool
from workflow.tool.context import ToolContext
from workflow.tool.google_docs.tool import GoogleDocsTool, GoogleDocsParam

logger = get_logger(__name__)


class GoogleDocsToolExecutor(BaseTool):
    """Executor for Google Docs tool operations using Composio"""
    
    name = "google_docs_fetch"
    param_class = GoogleDocsParam
    tool_definition = GoogleDocsTool
    execute_type = AgentExecuteType.FETCH_DOCUMENT
    
    def __init__(self):
        super().__init__()
        self.composio_client = None
        
    async def _initialize_client(self):
        """Initialize Composio client"""
        if not self.composio_client:
            import os
            api_key = os.getenv('COMPOSIO_API_KEY')
            if not api_key:
                raise ValueError("COMPOSIO_API_KEY not found in environment")
            self.composio_client = Composio(api_key=api_key)
    
    async def execute(self, params: GoogleDocsParam, context: ToolContext) -> Any:
        """
        Fetch Google Doc content using Composio
        
        Args:
            params: GoogleDocsParam with document ID
            context: Tool execution context
            
        Returns:
            Document content and metadata
        """
        await self._initialize_client()
        
        logger.info(f"Fetching Google Doc: {params.document_id}")
        
        # Send init message
        await self.send_init_message(
            context,
            execute_params={
                "document_id": params.document_id,
                "entity_id": params.entity_id
            }
        )
        
        try:
            # Send status update
            await context.on_client_message_text(f"Fetching document {params.document_id}...")
            
            # Execute GOOGLEDOCS_GET_DOCUMENT_BY_ID via Composio
            result = await asyncio.to_thread(
                self.composio_client.tools.execute,
                slug="GOOGLEDOCS_GET_DOCUMENT",  # The actual Composio action name
                arguments={"documentId": params.document_id},
                user_id=params.entity_id
            )
            
            # Extract document content
            document_data = self._extract_document_content(result)
            
            # Send success message
            doc_title = document_data.get("title", "Untitled")
            word_count = len(document_data.get("content", "").split())
            await context.on_client_message_text(
                f"✅ Successfully fetched document: {doc_title}\n"
                f"📝 Word count: {word_count}"
            )
            
            # Send complete message
            await self.send_complete_message(
                context,
                execute_result=document_data
            )
            
            return document_data
            
        except Exception as e:
            error_msg = f"Failed to fetch Google Doc: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await context.on_client_message_text(error_msg)
            
            await self.send_complete_message(
                context,
                execute_result={"error": error_msg}
            )
            
            return {"error": error_msg}
    
    def _extract_document_content(self, result: Any) -> Dict[str, Any]:
        """
        Extract and format document content from Composio response
        
        Args:
            result: Raw response from Composio
            
        Returns:
            Formatted document data
        """
        if not result:
            return {
                "title": "Untitled",
                "content": "",
                "document_id": "",
                "error": "No data returned"
            }
        
        # Handle different response structures from Composio
        if isinstance(result, dict):
            # Check for the data field
            data = result.get("data", result)
            
            # Extract document information
            doc_info = {
                "document_id": data.get("documentId", ""),
                "title": data.get("title", "Untitled"),
                "content": "",
                "body": data.get("body", {}),
                "headers": [],
                "lists": [],
                "tables": []
            }
            
            # Extract text content from body
            body = data.get("body", {})
            if body:
                content_parts = []
                
                # Extract content from structural elements
                content_elements = body.get("content", [])
                for element in content_elements:
                    if "paragraph" in element:
                        paragraph = element["paragraph"]
                        para_elements = paragraph.get("elements", [])
                        for para_elem in para_elements:
                            if "textRun" in para_elem:
                                text = para_elem["textRun"].get("content", "")
                                content_parts.append(text)
                                
                    elif "table" in element:
                        # Store table for structured parsing
                        doc_info["tables"].append(element["table"])
                        
                    elif "sectionBreak" in element:
                        content_parts.append("\n\n")
                
                doc_info["content"] = "".join(content_parts)
            
            # Alternative: check for direct text field
            if not doc_info["content"] and "text" in data:
                doc_info["content"] = data["text"]
            
            # Extract headers/footers if available
            if "headers" in data:
                doc_info["headers"] = list(data["headers"].values())
                
            # Extract named styles if needed for formatting
            if "namedStyles" in data:
                doc_info["named_styles"] = data["namedStyles"]
            
            return doc_info
            
        elif isinstance(result, str):
            # If result is just text content
            return {
                "title": "Document",
                "content": result,
                "document_id": ""
            }
        
        else:
            # Fallback for unknown structure
            return {
                "title": "Document",
                "content": str(result),
                "document_id": "",
                "raw_data": result
            }