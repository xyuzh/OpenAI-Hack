#!/usr/bin/env python
"""
Test the documents endpoint
"""
import requests
import json

def test_documents_endpoint():
    """Test the /api/documents endpoint"""
    
    base_url = "http://localhost:8000"
    entity_id = "default-user"
    
    print("Testing Documents Endpoint")
    print("=" * 60)
    
    # Test fetching documents
    url = f"{base_url}/api/documents"
    params = {"entity_id": entity_id}
    
    print(f"GET {url}")
    print(f"Params: {params}")
    print("-" * 60)
    
    try:
        response = requests.get(url, params=params)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success! Found {len(data.get('documents', []))} documents")
            
            # Print first document structure for debugging
            if data.get('documents'):
                print("\nFirst document structure:")
                doc = data['documents'][0]
                print(json.dumps(doc, indent=2))
        else:
            print(f"✗ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Error: Could not connect to server")
        print("Make sure the FastAPI server is running on port 8000")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_documents_endpoint()