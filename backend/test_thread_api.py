#!/usr/bin/env python3
"""
Test script for the thread-based API with Redis List/PubSub
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
    """Test /api/agent/{thread_id}/execute endpoint"""
    print(f"\n2. Testing task execution for thread {thread_id}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/agent/{thread_id}/execute",
            json={
                "task": "Write a simple Python hello world function",
                "context_data": [
                    {"type": "instruction", "content": "Create a hello world function that prints 'Hello, World!'"}
                ],
                "parameters": {"language": "python"},
                "user_uuid": "test_user"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Task submitted successfully: run_id={data['run_id']}")
            return data['run_id']
        else:
            print(f"✗ Failed to execute task: {response.status_code} - {response.text}")
            return None


async def test_stream_events(thread_id: str, max_events: int = 10):
    """Test /api/agent/{thread_id}/stream endpoint with Redis List/PubSub"""
    print(f"\n3. Testing event streaming for thread {thread_id}...")
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "GET",
                f"{BASE_URL}/api/agent/{thread_id}/stream",
                timeout=30.0
            ) as response:
                if response.status_code == 200:
                    print("✓ SSE connection established")
                    print(f"Receiving events (max {max_events}):")
                    
                    event_count = 0
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str:
                                try:
                                    data = json.loads(data_str)
                                    event_type = data.get('type', 'unknown')
                                    
                                    # Print event summary
                                    if event_type == 'task_agent_execute':
                                        agent_data = data.get('data', {})
                                        execute_type = agent_data.get('execute_type', '')
                                        print(f"  [{event_count+1}] Agent Event: {execute_type}")
                                        
                                        # Show details for specific types
                                        if execute_type == 'ASSISTANT_RESPONSE':
                                            result = agent_data.get('execute_result', {})
                                            response_text = result.get('assistant_response_result', '')
                                            if response_text:
                                                print(f"      Response: {response_text[:100]}...")
                                    
                                    elif event_type == 'status':
                                        status = data.get('status', 'unknown')
                                        print(f"  [{event_count+1}] Status: {status}")
                                        if status in ['completed', 'failed', 'stopped', 'error']:
                                            print("  Stream ended with status:", status)
                                            break
                                    
                                    elif event_type == 'keep_alive':
                                        print(f"  [{event_count+1}] Keep-alive signal")
                                    
                                    else:
                                        print(f"  [{event_count+1}] Event Type: {event_type}")
                                    
                                    event_count += 1
                                    if event_count >= max_events:
                                        print(f"  Reached max events ({max_events}), stopping...")
                                        break
                                    
                                except json.JSONDecodeError as e:
                                    print(f"  Failed to parse JSON: {e}")
                                    print(f"  Raw data: {data_str[:100]}...")
                else:
                    print(f"✗ Failed to establish SSE connection: {response.status_code}")
                    
        except httpx.ReadTimeout:
            print("  SSE connection timed out (expected for long-running tasks)")
        except Exception as e:
            print(f"✗ Error during streaming: {e}")


async def test_stream_with_resume(thread_id: str):
    """Test resuming stream from a specific point"""
    print(f"\n4. Testing stream resume for thread {thread_id}...")
    
    # First, get some initial events
    print("  Getting initial events...")
    last_index = 2  # Simulate having received first 3 messages (0, 1, 2)
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "GET",
                f"{BASE_URL}/api/agent/{thread_id}/stream",
                params={"last_id": str(last_index)},
                timeout=10.0
            ) as response:
                if response.status_code == 200:
                    print(f"✓ Resumed stream from index {last_index}")
                    
                    event_count = 0
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str:
                                try:
                                    data = json.loads(data_str)
                                    print(f"  Resumed Event: {data.get('type', 'unknown')}")
                                    event_count += 1
                                    if event_count >= 3:
                                        break
                                except json.JSONDecodeError:
                                    pass
                else:
                    print(f"✗ Failed to resume stream: {response.status_code}")
                    
        except httpx.ReadTimeout:
            print("  Resume test timed out")
        except Exception as e:
            print(f"✗ Error during resume test: {e}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Thread-Based Agent API with Redis List/PubSub")
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
    print("\n⏳ Waiting for task processing to start...")
    await asyncio.sleep(3)
    
    # Test 3: Stream events
    await test_stream_events(thread_id)
    
    # Test 4: Test resume functionality
    await test_stream_with_resume(thread_id)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed")
    print("=" * 60)
    print("\nNote: The agent task may still be running in the background.")
    print("You can continue streaming from the same thread_id to see more events.")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)