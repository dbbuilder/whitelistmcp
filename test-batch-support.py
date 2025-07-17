#!/usr/bin/env python3
"""Test batch request support."""

import json
import subprocess
import sys

def test_batch_requests():
    """Test various batch request scenarios."""
    
    # Test 1: Mixed batch with requests and notifications
    batch1 = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        },
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"  # No id - this is a notification
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
    ]
    
    print("Test 1: Mixed batch (2 requests + 1 notification)")
    print("Input:", json.dumps(batch1))
    
    # Test 2: Batch with only notifications
    batch2 = [
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        },
        {
            "jsonrpc": "2.0",
            "method": "$/progress",
            "params": {"message": "Working..."}
        }
    ]
    
    print("\nTest 2: Batch with only notifications")
    print("Input:", json.dumps(batch2))
    print("Expected output: (nothing - should return None)")
    
    # Test 3: Single request (not a batch)
    single = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "initialize",
        "params": {}
    }
    
    print("\nTest 3: Single request (not a batch)")
    print("Input:", json.dumps(single))
    
    # Test 4: Empty batch
    empty_batch = []
    
    print("\nTest 4: Empty batch")
    print("Input:", json.dumps(empty_batch))
    print("Expected output: (nothing)")

if __name__ == "__main__":
    test_batch_requests()