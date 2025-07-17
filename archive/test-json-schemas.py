#!/usr/bin/env python3
"""Test JSON schema extraction and validation."""

import json
import re

# Read the handler file and extract the credential schema
with open('/mnt/d/dev2/awswhitelist2/awswhitelist/mcp/handler.py', 'r') as f:
    content = f.read()

# Extract credential schema definition
cred_match = re.search(r'credential_schema = (\{.*?\})\s*tools = \[', content, re.DOTALL)
if cred_match:
    cred_schema_str = cred_match.group(1)
    # Clean up the string to make it valid JSON
    cred_schema_str = re.sub(r'(\w+):', r'"\1":', cred_schema_str)  # Quote keys
    cred_schema_str = cred_schema_str.replace("'", '"')  # Replace single quotes
    
    try:
        credential_schema = json.loads(cred_schema_str)
        print("✓ Credential schema is valid JSON:")
        print(json.dumps(credential_schema, indent=2))
    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse credential schema: {e}")
        print(f"Schema string: {cred_schema_str[:200]}...")

# Test a complete tool schema
test_tool = {
    "name": "whitelist_add",
    "description": "Add an IP address to an AWS Security Group",
    "inputSchema": {
        "type": "object",
        "properties": {
            "credentials": {
                "type": "object",
                "properties": {
                    "access_key_id": {"type": "string"},
                    "secret_access_key": {"type": "string"},
                    "region": {"type": "string"},
                    "session_token": {"type": "string"}
                },
                "required": ["access_key_id", "secret_access_key", "region"]
            },
            "security_group_id": {"type": "string", "description": "AWS Security Group ID (e.g., sg-12345678)"},
            "ip_address": {"type": "string", "description": "IP address or CIDR block to whitelist"},
            "port": {"type": "integer", "description": "Port number (default: 443)", "minimum": 1, "maximum": 65535},
            "protocol": {"type": "string", "enum": ["tcp", "udp", "icmp"], "description": "Protocol (default: tcp)"},
            "description": {"type": "string", "description": "Description for the security group rule"}
        },
        "required": ["credentials", "security_group_id", "ip_address"]
    }
}

print("\n" + "="*50)
print("Testing complete tool schema as JSON:")
try:
    json_str = json.dumps(test_tool, indent=2)
    print("✓ Tool schema is valid JSON")
    
    # Parse it back to verify
    parsed = json.loads(json_str)
    print("✓ Schema can be parsed back successfully")
    
    # Check specific validations
    print("\nValidation checks:")
    
    # Check that all required fields exist in properties
    schema = parsed["inputSchema"]
    for req in schema.get("required", []):
        if req in schema.get("properties", {}):
            print(f"  ✓ Required field '{req}' exists in properties")
        else:
            print(f"  ✗ Required field '{req}' NOT found in properties")
    
    # Check enum values
    protocol_enum = schema["properties"]["protocol"].get("enum")
    if protocol_enum:
        print(f"  ✓ Protocol enum values: {protocol_enum}")
    
    # Check port constraints
    port_schema = schema["properties"]["port"]
    if "minimum" in port_schema and "maximum" in port_schema:
        print(f"  ✓ Port has min/max constraints: {port_schema['minimum']}-{port_schema['maximum']}")
    
except json.JSONDecodeError as e:
    print(f"✗ Failed to create valid JSON: {e}")

# Test that the schema would validate properly
print("\n" + "="*50)
print("Testing schema validation with sample inputs:")

valid_input = {
    "credentials": {
        "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "region": "us-east-1"
    },
    "security_group_id": "sg-12345678",
    "ip_address": "192.168.1.1",
    "port": 443,
    "protocol": "tcp",
    "description": "Test rule"
}

print("\nValid input structure:")
print(json.dumps(valid_input, indent=2))

# Check JSON serialization
try:
    json_str = json.dumps(valid_input)
    parsed = json.loads(json_str)
    print("\n✓ Input can be serialized and deserialized successfully")
except Exception as e:
    print(f"\n✗ JSON serialization error: {e}")