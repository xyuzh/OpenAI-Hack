#!/usr/bin/env python
"""
Check and setup Composio auth configs
"""
import os
import asyncio
from dotenv import load_dotenv
from composio import Composio
from composio.client.enums import App

# Load environment variables
load_dotenv()


async def check_and_setup_auth_configs():
    """Check existing auth configs and create if needed"""
    
    api_key = os.getenv('COMPOSIO_API_KEY')
    if not api_key:
        print("Error: COMPOSIO_API_KEY not found in environment")
        return
    
    client = Composio(api_key=api_key)
    
    print("Checking existing auth configs...")
    print("=" * 50)
    
    try:
        # List existing auth configs
        auth_configs_response = client.auth_configs.list()
        
        # Convert response to list if needed
        auth_configs = []
        if auth_configs_response:
            if hasattr(auth_configs_response, 'items'):
                auth_configs = auth_configs_response.items
            elif hasattr(auth_configs_response, '__iter__'):
                auth_configs = list(auth_configs_response)
            else:
                auth_configs = [auth_configs_response]
        
        if auth_configs:
            print(f"Found {len(auth_configs)} auth config(s):")
            for config in auth_configs:
                print(f"\nAuth Config:")
                print(f"  ID: {getattr(config, 'id', 'N/A')}")
                print(f"  Toolkit: {getattr(config, 'toolkit', 'N/A')}")
                print(f"  Auth Type: {getattr(config, 'auth_type', 'N/A')}")
                print(f"  Status: {getattr(config, 'status', 'N/A')}")
                
                # Print all attributes for debugging
                for attr in dir(config):
                    if not attr.startswith('_'):
                        value = getattr(config, attr, None)
                        if value and not callable(value):
                            print(f"  {attr}: {value}")
        else:
            print("No auth configs found.")
            
        print("\n" + "=" * 50)
        print("Creating/Getting auth configs for required apps...")
        print("=" * 50)
        
        # Apps we need
        apps_needed = {
            'googledocs': 'GOOGLEDOCS',
            'gmail': 'GMAIL',
            'linear': 'LINEAR'
        }
        
        auth_config_map = {}
        
        for app_name, app_enum_name in apps_needed.items():
            print(f"\nProcessing {app_name}...")
            
            # Check if auth config already exists
            existing_config = None
            if auth_configs:
                for config in auth_configs:
                    toolkit = getattr(config, 'toolkit', '').lower()
                    if toolkit == app_name or toolkit == app_enum_name.lower():
                        existing_config = config
                        break
            
            if existing_config:
                config_id = getattr(existing_config, 'id', None)
                print(f"  ✓ Found existing config: {config_id}")
                auth_config_map[app_name] = config_id
            else:
                # Try to create new auth config
                try:
                    print(f"  Creating new auth config for {app_name}...")
                    # Use the app name as toolkit identifier
                    new_config = client.auth_configs.create(
                        toolkit=app_enum_name
                    )
                    config_id = getattr(new_config, 'id', None)
                    print(f"  ✓ Created new config: {config_id}")
                    auth_config_map[app_name] = config_id
                except Exception as e:
                    print(f"  ✗ Failed to create config: {e}")
        
        print("\n" + "=" * 50)
        print("Auth Config Map for composio_service.py:")
        print("=" * 50)
        print("\nauth_config_map = {")
        for app, config_id in auth_config_map.items():
            print(f"    '{app}': '{config_id}',")
        print("}")
        
        # Test connection initiation with the first available config
        if auth_config_map:
            print("\n" + "=" * 50)
            print("Testing connection initiation...")
            print("=" * 50)
            
            test_app = list(auth_config_map.keys())[0]
            test_config_id = auth_config_map[test_app]
            
            try:
                print(f"\nInitiating connection for {test_app}...")
                connection = client.connected_accounts.initiate(
                    user_id="test_user_123",
                    auth_config_id=test_config_id
                )
                
                print("✓ Connection initiated successfully!")
                print(f"  Redirect URL: {getattr(connection, 'redirect_url', 'N/A')}")
                print(f"  Connection ID: {getattr(connection, 'id', 'N/A')}")
            except Exception as e:
                print(f"✗ Failed to initiate connection: {e}")
                
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: You may need to:")
        print("1. Verify your COMPOSIO_API_KEY is correct")
        print("2. Set up OAuth apps in Composio dashboard first")
        print("3. Contact Composio support for help with auth configs")


if __name__ == "__main__":
    asyncio.run(check_and_setup_auth_configs())