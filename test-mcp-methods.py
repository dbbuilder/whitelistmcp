#!/usr/bin/env python3
"""Test MCP methods for awswhitelist server."""

import json
import subprocess
import sys
import time

def test_method(method, params=None, request_id=None):
    """Test a single MCP method."""
    print(f"\nTesting method: {method}")
    
    # Build request
    request = {
        "jsonrpc": "2.0",
        "method": method
    }
    
    if params is not None:
        request["params"] = params
    
    if request_id is not None:
        request["id"] = request_id
    
    # Run awswhitelist
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "awswhitelist.main"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send request
        request_json = json.dumps(request)
        stdout, stderr = process.communicate(input=request_json + "\n", timeout=2)
        
        # Check response
        if request_id is None:
            # Notification - no response expected
            if not stdout.strip():
                print("✓ SUCCESS - No response for notification (expected)")
            else:
                print(f"✗ ERROR - Unexpected response for notification: {stdout}")
        else:
            # Regular request - parse response
            try:
                response = json.loads(stdout.strip())
                if "result" in response:
                    print("✓ SUCCESS")
                    print(f"Result: {json.dumps(response['result'], indent=2)}")
                elif "error" in response:
                    print(f"✗ ERROR: {response['error']['message']}")
                else:
                    print(f"✗ Invalid response format: {response}")
            except json.JSONDecodeError as e:
                print(f"✗ Failed to parse response: {e}")
                print(f"Raw output: {stdout}")
        
        # Show any log messages
        if stderr.strip():
            print(f"Logs: {stderr[:200]}...")
            
    except subprocess.TimeoutExpired:
        print("✗ ERROR - Request timed out")
        process.kill()
    except Exception as e:
        print(f"✗ ERROR - Failed to run test: {e}")

def main():
    """Run all tests."""
    print("Testing awswhitelist MCP server methods...")
    
    # Test initialize
    test_method("initialize", {}, 1)
    
    # Test tools/list
    test_method("tools/list", {}, 2)
    
    # Test resources/list
    test_method("resources/list", {}, 3)
    
    # Test prompts/list
    test_method("prompts/list", {}, 4)
    
    # Test notification (no id)
    test_method("notifications/initialized", {})
    
    # Test invalid method
    test_method("invalid/method", {}, 5)
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()