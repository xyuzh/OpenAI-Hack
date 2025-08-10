"""
Composio Documents Controller
Handles fetching and managing Google Docs via Composio
"""
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from gateway.service.composio_service import get_composio_service
from common.utils.logger_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


class GoogleDoc(BaseModel):
    """Google Doc model matching frontend expectations"""
    id: str
    name: str
    mimeType: str
    createdTime: str
    modifiedTime: Optional[str]
    webViewLink: Optional[str]
    size: str
    starred: bool
    trashed: bool
    shared: bool
    owners: Optional[List[Dict[str, Any]]]
    lastModifyingUser: Optional[Dict[str, Any]]
    permissions: Optional[List[Dict[str, Any]]]


class DocumentsListResponse(BaseModel):
    """Response model for documents list"""
    documents: List[GoogleDoc]
    total_found: Optional[int] = None
    next_page_token: Optional[str] = None


@router.get("", response_model=DocumentsListResponse)
async def list_documents(
    entity_id: str = Query(..., description="User's entity ID"),
    query: Optional[str] = Query(None, description="Search query for documents"),
    page_size: Optional[int] = Query(100, description="Number of documents to return"),
    page_token: Optional[str] = Query(None, description="Token for pagination")
):
    """
    Fetch all Google Docs for a user
    
    This endpoint uses Composio's GOOGLEDOCS_SEARCH_DOCUMENTS tool to retrieve
    the user's Google Docs. The response format matches what the frontend expects.
    """
    try:
        logger.info(f"Fetching documents for entity {entity_id}, query: {query}")
        
        service = get_composio_service()
        
        # Check if user has Google Docs connected
        connection_status = await service.check_connection_status(
            entity_id=entity_id,
            app_name="googledocs"
        )
        
        if not connection_status.get("connected"):
            raise HTTPException(
                status_code=403,
                detail="Google Docs not connected. Please authenticate first."
            )
        
        # Fetch documents from Google Docs
        documents = await service.search_google_docs(
            entity_id=entity_id,
            query=query
        )
        
        # Return formatted response
        return DocumentsListResponse(
            documents=documents,
            total_found=len(documents)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch documents: {str(e)}"
        )


@router.get("/{document_id}")
async def get_document(
    document_id: str = Path(..., description="Google Doc ID"),
    entity_id: str = Query(..., description="User's entity ID")
):
    """
    Get details for a specific Google Doc
    
    Fetches detailed information about a single document.
    """
    try:
        logger.info(f"Fetching document {document_id} for entity {entity_id}")
        
        service = get_composio_service()
        
        # Check connection
        connection_status = await service.check_connection_status(
            entity_id=entity_id,
            app_name="googledocs"
        )
        
        if not connection_status.get("connected"):
            raise HTTPException(
                status_code=403,
                detail="Google Docs not connected. Please authenticate first."
            )
        
        # Try to get specific document
        # Note: This might require a different Composio tool
        result = await service.execute_tool(
            entity_id=entity_id,
            tool_name="GOOGLEDOCS_GET_DOCUMENT",
            params={"document_id": document_id}
        )
        
        if result and 'data' in result:
            return result['data']
        
        raise HTTPException(status_code=404, detail="Document not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch document: {str(e)}"
        )


@router.post("/{document_id}/generate")
async def generate_content(
    document_id: str = Path(..., description="Google Doc ID"),
    entity_id: str = Query(..., description="User's entity ID")
):
    """
    Generate content for a document (placeholder for AI generation)
    
    This endpoint can be used to trigger AI content generation for a document.
    """
    try:
        logger.info(f"Generating content for document {document_id}, entity {entity_id}")
        
        # This is a placeholder for content generation logic
        # You might want to:
        # 1. Fetch the document content
        # 2. Send it to OpenAI for processing
        # 3. Update the document with generated content
        
        return {
            "message": "Content generation initiated",
            "document_id": document_id,
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate content: {str(e)}"
        )


@router.get("/mock/test-data")
async def get_mock_documents():
    """
    Get mock document data for testing
    
    Returns the same format as the real documents endpoint but with test data.
    """
    mock_docs = [
        {
            "id": "1aRtvpOGGvW-FiwhrLQ7VYcmsyN5UI6yBDCFffUc7I-U",
            "name": "The Golden Gate's Whisper",
            "mimeType": "application/vnd.google-apps.document",
            "createdTime": "2025-08-07T17:24:26.726Z",
            "modifiedTime": "2025-08-07T17:24:27.798Z",
            "webViewLink": "https://docs.google.com/document/d/1aRtvpOGGvW-FiwhrLQ7VYcmsyN5UI6yBDCFffUc7I-U/edit",
            "size": "1701",
            "starred": False,
            "trashed": False,
            "shared": False,
            "owners": [
                {
                    "displayName": "Test User",
                    "emailAddress": "test@example.com",
                    "kind": "drive#user",
                    "photoLink": "https://via.placeholder.com/64"
                }
            ],
            "lastModifyingUser": {
                "displayName": "Test User",
                "emailAddress": "test@example.com",
                "kind": "drive#user",
                "photoLink": "https://via.placeholder.com/64"
            },
            "permissions": [
                {
                    "id": "05129666979744630922",
                    "displayName": "Test User",
                    "emailAddress": "test@example.com",
                    "role": "owner",
                    "type": "user",
                    "kind": "drive#permission"
                }
            ]
        },
        {
            "id": "2bRtvpOGGvW-FiwhrLQ7VYcmsyN5UI6yBDCFffUc7I-V",
            "name": "Project Planning Document",
            "mimeType": "application/vnd.google-apps.document",
            "createdTime": "2025-08-06T14:20:15.123Z",
            "modifiedTime": "2025-08-08T09:15:42.456Z",
            "webViewLink": "https://docs.google.com/document/d/2bRtvpOGGvW-FiwhrLQ7VYcmsyN5UI6yBDCFffUc7I-V/edit",
            "size": "3245",
            "starred": True,
            "trashed": False,
            "shared": True,
            "owners": [
                {
                    "displayName": "Test User",
                    "emailAddress": "test@example.com",
                    "kind": "drive#user",
                    "photoLink": "https://via.placeholder.com/64"
                }
            ],
            "lastModifyingUser": {
                "displayName": "Collaborator",
                "emailAddress": "collab@example.com",
                "kind": "drive#user",
                "photoLink": "https://via.placeholder.com/64"
            },
            "permissions": [
                {
                    "id": "05129666979744630922",
                    "displayName": "Test User",
                    "emailAddress": "test@example.com",
                    "role": "owner",
                    "type": "user",
                    "kind": "drive#permission"
                },
                {
                    "id": "05129666979744630923",
                    "displayName": "Collaborator",
                    "emailAddress": "collab@example.com",
                    "role": "writer",
                    "type": "user",
                    "kind": "drive#permission"
                }
            ]
        }
    ]
    
    return DocumentsListResponse(
        documents=mock_docs,
        total_found=len(mock_docs)
    )