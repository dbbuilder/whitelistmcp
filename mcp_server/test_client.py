#!/usr/bin/env python3
"""
Simple test client for AWS Security Group MCP Server
This demonstrates how an LLM agent would interact with the MCP server
"""

import json
import asyncio
from typing import Dict, Any

# Simulate MCP tool calls
class MCPTestClient:
    def __init__(self):
        # Import the AWS manager from the server
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from server import AWSSecurityGroupManager, SecurityGroupRule
        
        self.aws_manager = AWSSecurityGroupManager()
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate calling an MCP tool"""
        print(f"\n🔧 Calling tool: {tool_name}")
        print(f"📋 Arguments: {json.dumps(arguments, indent=2)}")
        
        if tool_name == "test_aws_connection":
            result = await self.aws_manager.test_connection()
        
        elif tool_name == "add_security_group_rule":
            from server import SecurityGroupRule
            rule = SecurityGroupRule(
                user_name=arguments["user_name"],
                user_ip=arguments["user_ip"],
                port=arguments["port"],
                security_group_id=arguments["security_group_id"],
                resource_name=arguments["resource_name"]
            )
            result = await self.aws_manager.add_rule(rule)
        
        elif tool_name == "list_security_group_rules":
            result = await self.aws_manager.list_rules(
                security_group_id=arguments["security_group_id"],
                port=arguments.get("port")
            )
        
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        
        print(f"✅ Result: {json.dumps(result, indent=2)}")
        return result

async def main():
    """Test the MCP server functionality"""
    client = MCPTestClient()
    
    print("=" * 60)
    print("AWS Security Group MCP Server Test Client")
    print("=" * 60)
    
    # Test 1: Connection test
    print("\n1️⃣ Testing AWS Connection...")
    await client.call_tool("test_aws_connection", {})
    
    # Test 2: List existing rules
    print("\n2️⃣ Listing existing rules...")
    await client.call_tool("list_security_group_rules", {
        "security_group_id": "sg-0f0df629567eb6344",
        "port": "8080"
    })
    
    # Test 3: Add a new rule (example)
    print("\n3️⃣ Example: Adding a new rule...")
    print("(This is just an example - modify the IP and parameters as needed)")
    
    example_rule = {
        "user_name": "test_user",
        "user_ip": "192.168.1.100",
        "port": "8443",
        "security_group_id": "sg-0f0df629567eb6344",
        "resource_name": "TestApp"
    }
    
    print(f"\nExample command that would be sent by an LLM agent:")
    print(f"Tool: add_security_group_rule")
    print(f"Arguments: {json.dumps(example_rule, indent=2)}")
    
    # Uncomment to actually add the rule:
    # await client.call_tool("add_security_group_rule", example_rule)

if __name__ == "__main__":
    asyncio.run(main())
