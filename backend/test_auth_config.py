#!/usr/bin/env python
"""
Test Composio auth config connection
"""
import os
from dotenv import load_dotenv
from composio import Composio

# Load environment variables
load_dotenv()

def test_connection():
    """Test connection initiation with real auth config"""
    
    api_key = os.getenv('COMPOSIO_API_KEY')
    if not api_key:
        print("Error: COMPOSIO_API_KEY not found")
        return
    
    client = Composio(api_key=api_key)
    
    # Test with Google Docs auth config
    auth_config_id = 'ac_XRVlhk6xfkpX'
    user_id = 'test_user_123'
    
    print(f"Testing connection initiation...")
    print(f"Auth Config ID: {auth_config_id}")
    print(f"User ID: {user_id}")
    print("-" * 50)
    
    try:
        connection = client.connected_accounts.initiate(
            user_id=user_id,
            auth_config_id=auth_config_id
        )
        
        print("✓ Connection initiated successfully!")
        print(f"\nConnection details:")
        
        # Print all attributes
        for attr in dir(connection):
            if not attr.startswith('_'):
                value = getattr(connection, attr, None)
                if value and not callable(value):
                    print(f"  {attr}: {value}")
        
        # Get the redirect URL specifically
        redirect_url = None
        if hasattr(connection, 'redirect_url'):
            redirect_url = connection.redirect_url
        elif hasattr(connection, 'redirectUrl'):
            redirect_url = connection.redirectUrl
        elif hasattr(connection, 'url'):
            redirect_url = connection.url
            
        if redirect_url:
            print(f"\n🔗 Redirect URL for OAuth:")
            print(f"   {redirect_url}")
            print("\nNext steps:")
            print("1. Open this URL in a browser")
            print("2. Complete the OAuth authorization")
            print("3. The connection will be established")
        
    except Exception as e:
        print(f"✗ Error initiating connection: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_connection()