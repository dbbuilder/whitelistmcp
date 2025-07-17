#!/usr/bin/env python3
"""Static analysis of JSON schemas in the handler file."""

import re
import json

# Read the handler file
with open('/mnt/d/dev2/awswhitelist2/awswhitelist/mcp/handler.py', 'r') as f:
    content = f.read()

# Find the tools array
tools_match = re.search(r'tools = \[(.*?)\s*\]\s*return create_mcp_response', content, re.DOTALL)
if not tools_match:
    print("Could not find tools array")
    exit(1)

# Extract just the tools definition
tools_str = tools_match.group(1)

# Check for common JSON schema issues
print("🔍 Static Analysis of JSON Schemas")
print("=" * 50)

# 1. Check for trailing commas (common JSON error)
print("\n1. Checking for trailing commas...")
trailing_comma_pattern = r',\s*[}\]]'
matches = re.findall(trailing_comma_pattern, tools_str)
if matches:
    print(f"  ⚠ Found {len(matches)} potential trailing commas")
else:
    print("  ✓ No trailing commas found")

# 2. Check for inconsistent quotes
print("\n2. Checking for quote consistency...")
single_quotes = len(re.findall(r"'[^']*':", tools_str))
double_quotes = len(re.findall(r'"[^"]*":', tools_str))
print(f"  Single quotes: {single_quotes}")
print(f"  Double quotes: {double_quotes}")
if single_quotes > 0:
    print("  ⚠ Found single quotes - JSON requires double quotes")
else:
    print("  ✓ All quotes are double quotes")

# 3. Check for boolean values
print("\n3. Checking for Python booleans vs JSON booleans...")
if "True" in tools_str or "False" in tools_str:
    print("  ⚠ Found Python-style booleans (True/False) - JSON uses lowercase (true/false)")
else:
    print("  ✓ No Python-style booleans found")

# 4. Check for None values
print("\n4. Checking for None values...")
if "None" in tools_str:
    print("  ⚠ Found Python None - JSON uses null")
else:
    print("  ✓ No Python None values found")

# 5. Check schema patterns
print("\n5. Checking schema patterns...")

# Look for properties that might have invalid "required" field
invalid_required_pattern = r'"[^"]+"\s*:\s*\{[^}]*"required"\s*:\s*(?:true|false|True|False)'
matches = re.findall(invalid_required_pattern, tools_str)
if matches:
    print(f"  ⚠ Found {len(matches)} properties with invalid 'required' field inside property definition")
else:
    print("  ✓ No invalid 'required' fields in property definitions")

# Check for consistent enum definitions
enum_pattern = r'"enum"\s*:\s*\[(.*?)\]'
enums = re.findall(enum_pattern, tools_str)
print(f"\n6. Found {len(enums)} enum definitions:")
for i, enum in enumerate(enums):
    print(f"  Enum {i+1}: [{enum}]")

# Check for consistent type definitions
type_pattern = r'"type"\s*:\s*"([^"]+)"'
types = re.findall(type_pattern, tools_str)
type_counts = {}
for t in types:
    type_counts[t] = type_counts.get(t, 0) + 1
print(f"\n7. Type usage:")
for t, count in sorted(type_counts.items()):
    print(f"  {t}: {count} times")

# Check for port constraints
port_pattern = r'"port"\s*:\s*\{([^}]+)\}'
ports = re.findall(port_pattern, tools_str)
print(f"\n8. Port field definitions ({len(ports)} found):")
for i, port in enumerate(ports):
    if "minimum" not in port or "maximum" not in port:
        print(f"  ⚠ Port {i+1} missing min/max constraints: {{{port}}}")
    else:
        print(f"  ✓ Port {i+1} has constraints: {{{port}}}")

# Check for consistent description patterns
desc_pattern = r'"description"\s*:\s*"([^"]+)"'
descriptions = re.findall(desc_pattern, tools_str)
print(f"\n9. Found {len(descriptions)} descriptions")
for desc in descriptions:
    if len(desc) < 5:
        print(f"  ⚠ Very short description: '{desc}'")

# Check required arrays
required_pattern = r'"required"\s*:\s*\[(.*?)\]'
required_arrays = re.findall(required_pattern, tools_str, re.DOTALL)
print(f"\n10. Required arrays ({len(required_arrays)} found):")
for i, req in enumerate(required_arrays):
    fields = re.findall(r'"([^"]+)"', req)
    print(f"  Tool {i+1} requires: {fields}")
    # Check if credentials is always required
    if "credentials" not in fields:
        print(f"    ⚠ Missing 'credentials' in required fields!")

# Look for potential variable references that should be actual schemas
print("\n11. Checking for variable references...")
var_pattern = r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*[,}]'
matches = re.findall(var_pattern, tools_str)
# Filter out known valid values
valid_values = {'true', 'false', 'null'}
suspicious_vars = [m for m in matches if m not in valid_values and not m.startswith('"')]
if suspicious_vars:
    print(f"  Found variable references: {set(suspicious_vars)}")
    print("  ✓ This is OK if 'credential_schema' is defined")
else:
    print("  ⚠ No variable references found - credential_schema might be hardcoded")

print("\n" + "=" * 50)
print("Analysis complete!")