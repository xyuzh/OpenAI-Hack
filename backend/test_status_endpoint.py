#!/usr/bin/env python
"""
Test the status endpoint directly
"""
import asyncio
from gateway.service.composio_service import get_composio_service

async def test_status():
    """Test checking connection status"""
    
    service = get_composio_service()
    
    # Test with default-user who has an active Google Docs connection
    entity_id = "default-user"
    app_name = "googledocs"
    
    print(f"Checking status for {app_name} with entity {entity_id}")
    print("-" * 50)
    
    try:
        status = await service.check_connection_status(entity_id, app_name)
        print(f"Status result: {status}")
        
        if status["connected"]:
            print(f"✓ {app_name} is connected for {entity_id}")
        else:
            print(f"✗ {app_name} is not connected for {entity_id}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Also test Gmail
    print("\n" + "-" * 50)
    app_name = "gmail"
    print(f"Checking status for {app_name} with entity {entity_id}")
    
    try:
        status = await service.check_connection_status(entity_id, app_name)
        print(f"Status result: {status}")
        
        if status["connected"]:
            print(f"✓ {app_name} is connected for {entity_id}")
        else:
            print(f"✗ {app_name} is not connected for {entity_id}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(test_status())