#!/usr/bin/env python
"""
Test script for Composio integration
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from gateway.service.composio_service import ComposioService


async def test_composio():
    """Test Composio service methods"""
    
    # Initialize service
    try:
        service = ComposioService()
        print("✓ Composio service initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize service: {e}")
        return
    
    # Test entity creation
    entity_id = "test_user_123"
    try:
        result = await service.get_or_create_entity(entity_id)
        print(f"✓ Entity handled: {result}")
    except Exception as e:
        print(f"✗ Failed to handle entity: {e}")
    
    # Test connection initiation (will fail without proper auth config)
    try:
        print("\nTesting connection initiation...")
        print("Note: This will fail without proper auth config IDs from Composio dashboard")
        
        # Try to initiate Google Docs connection
        result = await service.initiate_connection(
            entity_id=entity_id,
            app_name="googledocs"
        )
        print(f"✓ Connection initiated: {result}")
    except Exception as e:
        print(f"✗ Expected error (need real auth config): {e}")
        print("\nTo fix this:")
        print("1. Go to Composio dashboard")
        print("2. Create OAuth apps for Google Docs, Gmail, and Linear")
        print("3. Get the auth config IDs")
        print("4. Update auth_config_map in composio_service.py")


if __name__ == "__main__":
    asyncio.run(test_composio())