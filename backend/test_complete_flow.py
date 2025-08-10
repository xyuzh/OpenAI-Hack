#!/usr/bin/env python
"""
Test the complete auth and document fetch flow
"""
import asyncio
from gateway.service.composio_service import get_composio_service

async def test_complete_flow():
    """Test the complete flow"""
    
    service = get_composio_service()
    entity_id = "default-user"
    
    print("=" * 60)
    print("TESTING COMPLETE COMPOSIO FLOW")
    print("=" * 60)
    
    # 1. Check Google Docs connection status
    print("\n1. Checking Google Docs connection status...")
    try:
        status = await service.check_connection_status(entity_id, "googledocs")
        if status["connected"]:
            print("   ✓ Google Docs is connected")
        else:
            print("   ✗ Google Docs is not connected")
            print("   Please connect Google Docs first")
            return
    except Exception as e:
        print(f"   Error: {e}")
        return
    
    # 2. Check Gmail connection status
    print("\n2. Checking Gmail connection status...")
    try:
        status = await service.check_connection_status(entity_id, "gmail")
        if status["connected"]:
            print("   ✓ Gmail is connected")
        else:
            print("   ✗ Gmail is not connected")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 3. Fetch Google Docs
    print("\n3. Fetching Google Docs...")
    try:
        docs = await service.search_google_docs(entity_id)
        print(f"   ✓ Found {len(docs)} document(s)")
        
        if docs:
            print("\n   Documents:")
            for i, doc in enumerate(docs[:5], 1):  # Show first 5 docs
                print(f"   {i}. {doc.get('name', 'Untitled')}")
                print(f"      ID: {doc.get('id', 'N/A')}")
                print(f"      Modified: {doc.get('modifiedTime', 'N/A')}")
                print(f"      Link: {doc.get('webViewLink', 'N/A')}")
                print()
        else:
            print("   No documents found")
            
    except Exception as e:
        print(f"   Error fetching documents: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    return docs if 'docs' in locals() else []


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(test_complete_flow())