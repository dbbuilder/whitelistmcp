#!/usr/bin/env python3
"""Comprehensive JSON Schema validation check for MCP tool definitions."""

import json
import sys
import re
from typing import Dict, Any, List
import jsonschema
from jsonschema import Draft7Validator, validators

# Add the project to path
sys.path.insert(0, '/mnt/d/dev2/awswhitelist2')

# Import our handler to get the actual schemas
from awswhitelist.mcp.handler import MCPHandler, MCPRequest
from awswhitelist.config import Config

def extract_tool_schemas():
    """Extract the actual tool schemas from our handler."""
    # Create a dummy config and handler
    config = Config()
    handler = MCPHandler(config)
    
    # Create a dummy request for tools/list
    request = MCPRequest(
        jsonrpc="2.0",
        id=1,
        method="tools/list",
        params={}
    )
    
    # Get the response
    response = handler._handle_tools_list(request)
    
    # Extract tools from result
    return response.result["tools"]

def validate_schema_structure(schema: Dict[str, Any], path: str = "root") -> List[str]:
    """Validate a JSON schema structure and return any issues found."""
    issues = []
    
    # Check if it's a proper object
    if not isinstance(schema, dict):
        issues.append(f"{path}: Schema must be an object, got {type(schema)}")
        return issues
    
    # For object types, check properties
    if schema.get("type") == "object":
        # Check if properties is defined
        if "properties" in schema:
            if not isinstance(schema["properties"], dict):
                issues.append(f"{path}.properties: Must be an object")
            else:
                # Recursively check each property
                for prop_name, prop_schema in schema["properties"].items():
                    issues.extend(validate_schema_structure(prop_schema, f"{path}.properties.{prop_name}"))
        
        # Check required array
        if "required" in schema:
            if not isinstance(schema["required"], list):
                issues.append(f"{path}.required: Must be an array")
            else:
                # Check that all required fields exist in properties
                if "properties" in schema:
                    for req_field in schema["required"]:
                        if req_field not in schema["properties"]:
                            issues.append(f"{path}.required: Field '{req_field}' not found in properties")
    
    # Check for invalid keys in property definitions
    valid_property_keys = {
        "type", "description", "enum", "minimum", "maximum", "minLength", "maxLength",
        "pattern", "format", "properties", "required", "items", "additionalProperties",
        "default", "examples", "const", "nullable"
    }
    
    invalid_keys = set(schema.keys()) - valid_property_keys
    if invalid_keys and path != "root":  # root can have other keys
        issues.append(f"{path}: Invalid keys found: {invalid_keys}")
    
    # Check enum values
    if "enum" in schema:
        if not isinstance(schema["enum"], list):
            issues.append(f"{path}.enum: Must be an array")
        elif len(schema["enum"]) == 0:
            issues.append(f"{path}.enum: Must have at least one value")
    
    # Check type values
    if "type" in schema:
        valid_types = {"string", "number", "integer", "boolean", "array", "object", "null"}
        if schema["type"] not in valid_types:
            issues.append(f"{path}.type: Invalid type '{schema['type']}', must be one of {valid_types}")
    
    # Check numeric constraints
    if schema.get("type") in ("number", "integer"):
        if "minimum" in schema and "maximum" in schema:
            if schema["minimum"] > schema["maximum"]:
                issues.append(f"{path}: minimum ({schema['minimum']}) cannot be greater than maximum ({schema['maximum']})")
    
    return issues

def check_tool_naming(tools: List[Dict[str, Any]]) -> List[str]:
    """Check tool naming conventions."""
    issues = []
    
    for tool in tools:
        name = tool.get("name", "")
        
        # Check name format (should be namespace/action)
        if "/" not in name:
            issues.append(f"Tool '{name}': Name should follow namespace/action format")
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$', name):
            issues.append(f"Tool '{name}': Name contains invalid characters")
        
        # Check description
        if not tool.get("description"):
            issues.append(f"Tool '{name}': Missing description")
        elif len(tool["description"]) < 10:
            issues.append(f"Tool '{name}': Description too short")
    
    return issues

def validate_example_inputs(tool: Dict[str, Any]) -> List[str]:
    """Validate example inputs against the schema."""
    issues = []
    name = tool.get("name", "unknown")
    schema = tool.get("inputSchema", {})
    
    # Create test inputs based on the tool
    test_cases = []
    
    if name == "whitelist/add":
        test_cases = [
            # Valid minimal
            {
                "credentials": {
                    "access_key_id": "AKIATEST",
                    "secret_access_key": "secret",
                    "region": "us-east-1"
                },
                "security_group_id": "sg-12345",
                "ip_address": "1.2.3.4"
            },
            # Valid with all fields
            {
                "credentials": {
                    "access_key_id": "AKIATEST",
                    "secret_access_key": "secret",
                    "region": "us-east-1",
                    "session_token": "token"
                },
                "security_group_id": "sg-12345",
                "ip_address": "1.2.3.4/32",
                "port": 443,
                "protocol": "tcp",
                "description": "Test rule"
            },
            # Invalid - bad port
            {
                "credentials": {
                    "access_key_id": "AKIATEST",
                    "secret_access_key": "secret",
                    "region": "us-east-1"
                },
                "security_group_id": "sg-12345",
                "ip_address": "1.2.3.4",
                "port": 70000  # Too high
            },
            # Invalid - bad protocol
            {
                "credentials": {
                    "access_key_id": "AKIATEST",
                    "secret_access_key": "secret",
                    "region": "us-east-1"
                },
                "security_group_id": "sg-12345",
                "ip_address": "1.2.3.4",
                "protocol": "invalid"
            }
        ]
    
    # Validate test cases
    validator = Draft7Validator(schema)
    for i, test_input in enumerate(test_cases):
        errors = list(validator.iter_errors(test_input))
        if i < 2:  # First two should be valid
            if errors:
                issues.append(f"Tool '{name}' test case {i} should be valid but has errors: {[e.message for e in errors]}")
        else:  # Rest should be invalid
            if not errors:
                issues.append(f"Tool '{name}' test case {i} should be invalid but passed validation")
    
    return issues

def check_consistency(tools: List[Dict[str, Any]]) -> List[str]:
    """Check consistency across tools."""
    issues = []
    
    # All tools should have the same credential schema
    cred_schemas = {}
    for tool in tools:
        name = tool.get("name", "unknown")
        if "inputSchema" in tool and "properties" in tool["inputSchema"]:
            if "credentials" in tool["inputSchema"]["properties"]:
                cred_schema = json.dumps(tool["inputSchema"]["properties"]["credentials"], sort_keys=True)
                cred_schemas[name] = cred_schema
    
    # Check if all credential schemas are the same
    unique_schemas = set(cred_schemas.values())
    if len(unique_schemas) > 1:
        issues.append(f"Inconsistent credential schemas found across tools: {list(cred_schemas.keys())}")
    
    # Check that all tools with port also have protocol
    for tool in tools:
        name = tool.get("name", "unknown")
        props = tool.get("inputSchema", {}).get("properties", {})
        if "port" in props and "protocol" not in props:
            issues.append(f"Tool '{name}': Has 'port' but missing 'protocol'")
    
    return issues

def main():
    """Run comprehensive schema validation."""
    print("🔍 Comprehensive JSON Schema Validation Check")
    print("=" * 50)
    
    try:
        # Extract actual tool schemas
        tools = extract_tool_schemas()
        print(f"✓ Found {len(tools)} tools to validate\n")
        
        all_issues = []
        
        # 1. Validate each tool's schema structure
        print("1. Checking schema structure...")
        for tool in tools:
            name = tool.get("name", "unknown")
            schema = tool.get("inputSchema", {})
            
            # Validate against JSON Schema Draft 7
            try:
                Draft7Validator.check_schema(schema)
                print(f"  ✓ {name}: Valid JSON Schema")
            except jsonschema.exceptions.SchemaError as e:
                print(f"  ✗ {name}: Invalid schema - {e.message}")
                all_issues.append(f"{name}: {e.message}")
            
            # Additional structure checks
            issues = validate_schema_structure(schema, f"{name}.inputSchema")
            if issues:
                for issue in issues:
                    print(f"  ⚠ {issue}")
                all_issues.extend(issues)
        
        # 2. Check tool naming conventions
        print("\n2. Checking tool naming conventions...")
        naming_issues = check_tool_naming(tools)
        if naming_issues:
            for issue in naming_issues:
                print(f"  ⚠ {issue}")
            all_issues.extend(naming_issues)
        else:
            print("  ✓ All tool names follow conventions")
        
        # 3. Check consistency across tools
        print("\n3. Checking consistency across tools...")
        consistency_issues = check_consistency(tools)
        if consistency_issues:
            for issue in consistency_issues:
                print(f"  ⚠ {issue}")
            all_issues.extend(consistency_issues)
        else:
            print("  ✓ Tools are consistent")
        
        # 4. Validate example inputs
        print("\n4. Validating example inputs...")
        for tool in tools:
            example_issues = validate_example_inputs(tool)
            if example_issues:
                for issue in example_issues:
                    print(f"  ⚠ {issue}")
                all_issues.extend(example_issues)
        
        # 5. Check for common mistakes
        print("\n5. Checking for common mistakes...")
        for tool in tools:
            name = tool.get("name", "unknown")
            schema = tool.get("inputSchema", {})
            
            # Check for empty required arrays
            if schema.get("required") == []:
                print(f"  ⚠ {name}: Empty required array")
                all_issues.append(f"{name}: Empty required array")
            
            # Check for properties without type
            if "properties" in schema:
                for prop_name, prop_schema in schema["properties"].items():
                    if isinstance(prop_schema, dict) and "type" not in prop_schema:
                        print(f"  ⚠ {name}.{prop_name}: Missing type")
                        all_issues.append(f"{name}.{prop_name}: Missing type")
        
        # Final summary
        print("\n" + "=" * 50)
        if all_issues:
            print(f"❌ Found {len(all_issues)} issues that need fixing")
        else:
            print("✅ All schemas are valid and well-formed!")
            
        # Pretty print one schema as example
        print("\nExample schema (whitelist/add):")
        add_tool = next((t for t in tools if t["name"] == "whitelist/add"), None)
        if add_tool:
            print(json.dumps(add_tool["inputSchema"], indent=2))
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()