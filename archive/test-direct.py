#!/usr/bin/env python3
"""Direct test of MCP server."""

import sys
sys.path.insert(0, '.')

from awswhitelist.main import MCPServer

# Test basic functionality
try:
    server = MCPServer()
    
    # Test initialize
    response = server.process_request('{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}')
    print("Initialize response:", response)
    
    # Test tools/list
    response = server.process_request('{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}')
    print("\nTools/list response:", response[:200], "..." if len(response) > 200 else "")
    
    # Test notification
    response = server.process_request('{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}')
    print("\nNotification response:", repr(response))
    
    print("\n✓ All tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()