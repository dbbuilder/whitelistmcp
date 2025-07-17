#!/usr/bin/env python3
"""Test that tool names are using underscores."""

import sys
import os

# Add the project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from awswhitelist.mcp.handler import MCPHandler, MCPRequest
from awswhitelist.config import Config

# Create handler
config = Config()
handler = MCPHandler(config)

# Create request
request = MCPRequest(
    jsonrpc="2.0",
    id=1,
    method="tools/list",
    params={}
)

# Get response
response = handler._handle_tools_list(request)

# Check tool names
print("Tool names:")
for tool in response.result["tools"]:
    name = tool["name"]
    print(f"  - {name}")
    if "/" in name:
        print(f"    WARNING: Tool name contains slash!")
    if "_" in name:
        print(f"    ✓ Using underscore format")

print(f"\nTotal tools: {len(response.result['tools'])}")