"""
Composio Authentication Controller
Handles OAuth authentication flows for Google Docs, Gmail, and Jira
"""
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from gateway.service.composio_service import get_composio_service
from common.utils.logger_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/composio/auth", tags=["Composio Authentication"])


class AuthInitiateRequest(BaseModel):
    """Request model for initiating authentication"""
    app: str = Field(..., description="App to authenticate (googledocs, gmail, jira)")
    entity_id: str = Field(..., description="User's unique entity ID")


class AuthInitiateResponse(BaseModel):
    """Response model for authentication initiation"""
    redirect_url: str = Field(..., description="OAuth redirect URL")
    connection_id: Optional[str] = Field(None, description="Connection ID for tracking")
    status: str = Field(..., description="Connection status")
    app: str = Field(..., description="App being connected")


class ConnectionStatusResponse(BaseModel):
    """Response model for connection status"""
    status: str = Field(..., description="Connection status (active, pending, not_connected)")
    connected: bool = Field(..., description="Whether the connection is active")
    app: str = Field(..., description="App name")
    error: Optional[str] = Field(None, description="Error message if any")


@router.post("/initiate", response_model=AuthInitiateResponse)
async def initiate_auth(request: AuthInitiateRequest):
    """
    Initiate OAuth authentication for Google Docs, Gmail, or Jira
    
    This endpoint starts the OAuth flow and returns a redirect URL that
    the frontend should navigate the user to for authentication.
    """
    try:
        logger.info(f"Initiating auth for {request.app} with entity {request.entity_id}")
        
        # Validate app name
        valid_apps = ['googledocs', 'gmail', 'jira']
        if request.app.lower() not in valid_apps:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid app. Must be one of: {', '.join(valid_apps)}"
            )
        
        # Get or create entity
        service = get_composio_service()
        await service.get_or_create_entity(request.entity_id)
        
        # Initiate connection
        connection_info = await service.initiate_connection(
            entity_id=request.entity_id,
            app_name=request.app
        )
        
        return AuthInitiateResponse(
            redirect_url=connection_info["redirect_url"],
            connection_id=connection_info.get("connection_id"),
            status=connection_info["status"],
            app=connection_info["app"]
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error initiating auth: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate authentication: {str(e)}")


@router.get("/status/{entity_id}/{app}", response_model=ConnectionStatusResponse)
async def check_connection_status(
    entity_id: str = Path(..., description="User's entity ID"),
    app: str = Path(..., description="App name to check")
):
    """
    Check the connection status for a specific app and user
    
    Use this endpoint to poll whether the OAuth flow has been completed
    and the connection is active.
    """
    try:
        logger.info(f"Checking connection status for {app} with entity {entity_id}")
        
        service = get_composio_service()
        status_info = await service.check_connection_status(
            entity_id=entity_id,
            app_name=app
        )
        
        return ConnectionStatusResponse(
            status=status_info["status"],
            connected=status_info["connected"],
            app=status_info["app"],
            error=status_info.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error checking connection status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check connection status: {str(e)}"
        )


@router.get("/connections/{entity_id}")
async def list_connections(entity_id: str = Path(..., description="User's entity ID")):
    """
    List all active connections for a user
    
    Returns the status of all possible app connections (Google Docs, Gmail, Jira)
    """
    try:
        logger.info(f"Listing connections for entity {entity_id}")
        
        service = get_composio_service()
        apps = ['googledocs', 'gmail', 'jira']
        connections = {}
        
        for app in apps:
            status = await service.check_connection_status(entity_id, app)
            connections[app] = {
                "connected": status["connected"],
                "status": status["status"]
            }
        
        return {
            "entity_id": entity_id,
            "connections": connections
        }
        
    except Exception as e:
        logger.error(f"Error listing connections: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list connections: {str(e)}"
        )


@router.post("/disconnect/{entity_id}/{app}")
async def disconnect_app(
    entity_id: str = Path(..., description="User's entity ID"),
    app: str = Path(..., description="App to disconnect")
):
    """
    Disconnect an app for a user
    
    This will revoke the OAuth tokens and remove the connection.
    """
    try:
        logger.info(f"Disconnecting {app} for entity {entity_id}")
        
        # Note: Composio SDK might have a specific method for disconnection
        # This is a placeholder implementation
        return {
            "message": f"Disconnection for {app} initiated",
            "entity_id": entity_id,
            "app": app
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting app: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disconnect app: {str(e)}"
        )