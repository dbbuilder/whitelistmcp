#!/usr/bin/env python3
"""Update all method names from slash to underscore format."""

import os
import re

# Files to update
files_to_update = [
    "tests/unit/test_mcp_handler.py",
    "tests/integration/test_integration.py",
    "comprehensive-schema-check.py",
    "test-json-schemas.py",
]

# Patterns to replace
replacements = [
    ("whitelist/add", "whitelist_add"),
    ("whitelist/remove", "whitelist_remove"),
    ("whitelist/list", "whitelist_list"),
    ("whitelist/check", "whitelist_check"),
]

def update_file(filepath):
    """Update method names in a file."""
    if not os.path.exists(filepath):
        print(f"⚠ File not found: {filepath}")
        return
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    for old, new in replacements:
        # Update in strings
        content = content.replace(f'"{old}"', f'"{new}"')
        content = content.replace(f"'{old}'", f"'{new}'")
        # Update in comments
        content = content.replace(f" {old} ", f" {new} ")
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Updated: {filepath}")
    else:
        print(f"  No changes: {filepath}")

# Update all files
for filepath in files_to_update:
    update_file(filepath)

print("\nDone!")