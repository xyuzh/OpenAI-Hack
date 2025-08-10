#!/usr/bin/env python
"""
Test connection status checking
"""
import os
from dotenv import load_dotenv
from composio import Composio

# Load environment variables
load_dotenv()

def test_connection_status():
    """Test checking connection status"""
    
    api_key = os.getenv('COMPOSIO_API_KEY')
    if not api_key:
        print("Error: COMPOSIO_API_KEY not found")
        return
    
    client = Composio(api_key=api_key)
    
    print("Fetching all connected accounts...")
    print("=" * 50)
    
    try:
        # List all connected accounts
        connections_response = client.connected_accounts.list()
        
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
            
        if connections:
            print(f"Found {len(connections)} connection(s):")
            for conn in connections:
                print(f"\nConnection:")
                # Print all attributes
                for attr in dir(conn):
                    if not attr.startswith('_'):
                        value = getattr(conn, attr, None)
                        if value and not callable(value):
                            print(f"  {attr}: {value}")
                print("-" * 30)
        else:
            print("No connected accounts found.")
            
        # Now test filtering for a specific user
        test_user_id = "test_user_123"
        print(f"\nFiltering for user: {test_user_id}")
        print("=" * 50)
        
        if connections:
            user_connections = [
                c for c in connections 
                if hasattr(c, 'user_id') and c.user_id == test_user_id
            ]
            
            if user_connections:
                print(f"Found {len(user_connections)} connection(s) for {test_user_id}")
                for conn in user_connections:
                    print(f"  - App: {getattr(conn, 'app', 'N/A')}")
                    print(f"    Status: {getattr(conn, 'status', 'N/A')}")
                    print(f"    ID: {getattr(conn, 'id', 'N/A')}")
            else:
                print(f"No connections found for {test_user_id}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_connection_status()