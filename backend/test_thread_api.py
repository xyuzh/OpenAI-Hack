#!/usr/bin/env python3
"""
Test script for the new thread-based API endpoints
"""
import asyncio
import json
import httpx
import sys
from typing import Optional

BASE_URL = "http://localhost:8000"


async def test_initiate_thread():
    """Test /api/agent/initiate endpoint"""
    print("\n1. Testing thread initiation...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/agent/initiate",
            json={
                "metadata": {"name": "Test Thread", "purpose": "API Testing"},
                "context": {"initial_state": "ready"}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Thread created successfully: {data['thread_id']}")
            return data['thread_id']
        else:
            print(f"✗ Failed to create thread: {response.status_code} - {response.text}")
            return None


async def test_execute_task(thread_id: str):
    """Test /api/agent-run/{thread_id}/execute endpoint"""
    print(f"\n2. Testing task execution for thread {thread_id}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/agent/{thread_id}/execute",
            json={
                "task": "Write a simple Python hello world function",
                "context_data": [
                    {"type": "instruction", "content": "Create a hello world function"}
                ],
                "parameters": {"language": "python"}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Task submitted successfully: run_id={data['run_id']}")
            return data['run_id']
        else:
            print(f"✗ Failed to execute task: {response.status_code} - {response.text}")
            return None


async def test_stream_events(thread_id: str):
    """Test /api/agent-run/{thread_id}/stream endpoint"""
    print(f"\n3. Testing event streaming for thread {thread_id}...")
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "GET",
                f"{BASE_URL}/api/agent/{thread_id}/stream",
                timeout=10.0
            ) as response:
                if response.status_code == 200:
                    print("✓ SSE connection established")
                    print("Receiving events (will timeout after 10 seconds):")
                    
                    event_count = 0
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                            print(f"  Event: {event_type}")
                            event_count += 1
                            
                            # Stop after receiving a few events
                            if event_count >= 3:
                                print("  (Stopping after 3 events)")
                                break
                        elif line.startswith("data:"):
                            data = line[5:].strip()
                            if data:
                                try:
                                    parsed = json.loads(data)
                                    print(f"  Data: {json.dumps(parsed, indent=2)[:200]}...")
                                except json.JSONDecodeError:
                                    print(f"  Data: {data[:200]}...")
                else:
                    print(f"✗ Failed to establish SSE connection: {response.status_code}")
                    
        except httpx.ReadTimeout:
            print("  SSE connection timed out (expected for this test)")
        except Exception as e:
            print(f"✗ Error during streaming: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Thread-Based Agent API")
    print("=" * 60)
    
    # Test 1: Initiate thread
    thread_id = await test_initiate_thread()
    if not thread_id:
        print("\n❌ Failed to create thread, stopping tests")
        return 1
    
    # Test 2: Execute task
    run_id = await test_execute_task(thread_id)
    if not run_id:
        print("\n⚠️  Failed to execute task, but continuing...")
    
    # Small delay to allow task processing to start
    await asyncio.sleep(2)
    
    # Test 3: Stream events
    await test_stream_events(thread_id)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)