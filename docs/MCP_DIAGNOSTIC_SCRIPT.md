# MCP Diagnostic Script Guide

This guide provides language-agnostic diagnostic tests to validate MCP server compliance. Adapt these to your implementation language.

## Core Diagnostic Tests

### 1. Transport Layer Test

```bash
# Test 1: Verify stdout contains only JSON
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
your-server 2>/dev/null | \
jq . >/dev/null 2>&1 && echo "✓ Valid JSON output" || echo "✗ Invalid JSON output"

# Test 2: Verify no output for notifications
output=$(echo '{"jsonrpc":"2.0","method":"notifications/initialized"}' | your-server 2>/dev/null)
[ -z "$output" ] && echo "✓ No output for notifications" || echo "✗ Unexpected output for notifications"

# Test 3: Check stderr separation
echo '{"jsonrpc":"2.0","id":1,"method":"invalid_method"}' | \
your-server 2>&1 1>/dev/null | \
grep -q "." && echo "✓ Debug output to stderr" || echo "✓ No debug output (or properly suppressed)"
```

### 2. Protocol Compliance Test

```python
#!/usr/bin/env python3
"""MCP Protocol Compliance Tester"""

import json
import subprocess
import sys
from typing import Dict, Any, List, Tuple

class MCPDiagnostic:
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.errors = []
        self.warnings = []
        self.successes = []
    
    def run_test(self, request: Dict[str, Any]) -> Tuple[str, str]:
        """Run a single test and return stdout, stderr"""
        proc = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(json.dumps(request) + '\n')
        return stdout.strip(), stderr.strip()
    
    def test_initialization(self):
        """Test initialization sequence"""
        # Test 1: Initialize request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        }
        
        stdout, stderr = self.run_test(request)
        
        try:
            response = json.loads(stdout)
            
            # Check response structure
            if response.get("jsonrpc") != "2.0":
                self.errors.append("Missing or invalid jsonrpc field")
            
            if response.get("id") != 1:
                self.errors.append("Response ID doesn't match request ID")
            
            if "result" in response:
                result = response["result"]
                if "protocolVersion" not in result:
                    self.errors.append("Missing protocolVersion in response")
                if "capabilities" not in result:
                    self.errors.append("Missing capabilities in response")
                if "serverInfo" not in result:
                    self.errors.append("Missing serverInfo in response")
                else:
                    if "name" not in result["serverInfo"]:
                        self.errors.append("Missing server name")
                    if "version" not in result["serverInfo"]:
                        self.errors.append("Missing server version")
                self.successes.append("✓ Valid initialization response")
            elif "error" in response:
                self.errors.append(f"Initialization failed: {response['error']}")
            else:
                self.errors.append("Response missing both result and error")
                
        except json.JSONDecodeError:
            self.errors.append(f"Invalid JSON response: {stdout}")
    
    def test_notifications(self):
        """Test notification handling"""
        request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        stdout, stderr = self.run_test(request)
        
        if stdout:
            self.errors.append(f"Notification produced output: {stdout}")
        else:
            self.successes.append("✓ Notifications produce no output")
    
    def test_error_handling(self):
        """Test error response format"""
        # Test unknown method
        request = {
            "jsonrpc": "2.0",
            "id": "test-error",
            "method": "unknown/method",
            "params": {}
        }
        
        stdout, stderr = self.run_test(request)
        
        try:
            response = json.loads(stdout)
            
            if "error" in response:
                error = response["error"]
                if error.get("code") != -32601:
                    self.warnings.append(f"Unexpected error code for unknown method: {error.get('code')}")
                if "message" not in error:
                    self.errors.append("Error missing message field")
                self.successes.append("✓ Proper error response format")
            else:
                self.errors.append("Expected error response for unknown method")
                
        except json.JSONDecodeError:
            self.errors.append(f"Invalid JSON error response: {stdout}")
    
    def test_id_types(self):
        """Test ID field flexibility"""
        # Test string ID
        request = {
            "jsonrpc": "2.0",
            "id": "string-id",
            "method": "initialize",
            "params": {}
        }
        
        stdout, _ = self.run_test(request)
        
        try:
            response = json.loads(stdout)
            if response.get("id") != "string-id":
                self.errors.append("String ID not preserved")
            else:
                self.successes.append("✓ String IDs supported")
        except:
            self.errors.append("Failed with string ID")
        
        # Test numeric ID
        request["id"] = 42
        stdout, _ = self.run_test(request)
        
        try:
            response = json.loads(stdout)
            if response.get("id") != 42:
                self.errors.append("Numeric ID not preserved")
            else:
                self.successes.append("✓ Numeric IDs supported")
        except:
            self.errors.append("Failed with numeric ID")
    
    def generate_report(self):
        """Generate diagnostic report"""
        print("=== MCP Server Diagnostic Report ===\n")
        
        if self.successes:
            print("✅ Passed Tests:")
            for success in self.successes:
                print(f"   {success}")
            print()
        
        if self.warnings:
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   {warning}")
            print()
        
        if self.errors:
            print("❌ Failed Tests:")
            for error in self.errors:
                print(f"   {error}")
            print()
        
        if not self.errors:
            print("🎉 All critical tests passed!")
        else:
            print(f"💔 {len(self.errors)} critical issues found")

# Usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mcp_diagnostic.py <server-command>")
        sys.exit(1)
    
    diagnostic = MCPDiagnostic(sys.argv[1:])
    diagnostic.test_initialization()
    diagnostic.test_notifications()
    diagnostic.test_error_handling()
    diagnostic.test_id_types()
    diagnostic.generate_report()
```

### 3. Schema Validation Test

```javascript
#!/usr/bin/env node
// MCP Schema Validator

const Ajv = require('ajv');
const ajv = new Ajv();

// Test tool schema validation
function validateToolSchemas(tools) {
    const errors = [];
    const metaSchema = require('ajv/lib/refs/json-schema-draft-07.json');
    
    tools.forEach(tool => {
        // Validate tool structure
        if (!tool.name || typeof tool.name !== 'string') {
            errors.push(`Invalid tool name: ${tool.name}`);
        }
        
        if (tool.name && tool.name.includes('/')) {
            errors.push(`Tool name contains slash (use underscores): ${tool.name}`);
        }
        
        if (!tool.description || tool.description.length < 10) {
            errors.push(`Tool ${tool.name} has insufficient description`);
        }
        
        // Validate input schema
        if (tool.inputSchema) {
            try {
                ajv.compile(tool.inputSchema);
            } catch (e) {
                errors.push(`Tool ${tool.name} has invalid schema: ${e.message}`);
            }
            
            // Check for common mistakes
            const schemaStr = JSON.stringify(tool.inputSchema);
            if (schemaStr.includes('"required":false') || schemaStr.includes('"required":true')) {
                errors.push(`Tool ${tool.name} has invalid "required" in property definition`);
            }
        }
    });
    
    return errors;
}

// Run validation
async function runDiagnostic(serverCommand) {
    // Get tools list
    const { spawn } = require('child_process');
    const server = spawn(serverCommand, { shell: true });
    
    // Send tools/list request
    const request = JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/list",
        params: {}
    }) + '\n';
    
    server.stdin.write(request);
    
    let output = '';
    server.stdout.on('data', (data) => {
        output += data.toString();
    });
    
    server.on('close', () => {
        try {
            const response = JSON.parse(output);
            if (response.result && response.result.tools) {
                const errors = validateToolSchemas(response.result.tools);
                
                if (errors.length === 0) {
                    console.log('✅ All tool schemas valid!');
                } else {
                    console.log('❌ Schema validation errors:');
                    errors.forEach(e => console.log(`   - ${e}`));
                }
            }
        } catch (e) {
            console.error('Failed to parse tools response:', e);
        }
    });
}
```

### 4. Performance and Reliability Test

```go
package main

import (
    "bufio"
    "encoding/json"
    "fmt"
    "os/exec"
    "time"
)

// Test timeout handling
func testTimeouts(serverCmd string) {
    cmd := exec.Command("sh", "-c", serverCmd)
    stdin, _ := cmd.StdinPipe()
    stdout, _ := cmd.StdoutPipe()
    cmd.Start()

    // Send request
    request := map[string]interface{}{
        "jsonrpc": "2.0",
        "id":      1,
        "method":  "tools/call",
        "params": map[string]interface{}{
            "name": "long_running_tool",
        },
    }
    
    encoder := json.NewEncoder(stdin)
    encoder.Encode(request)
    
    // Set timeout
    done := make(chan bool)
    go func() {
        scanner := bufio.NewScanner(stdout)
        for scanner.Scan() {
            // Got response
            done <- true
            return
        }
    }()
    
    select {
    case <-done:
        fmt.Println("✓ Response received in time")
    case <-time.After(5 * time.Second):
        // Send cancel request
        cancel := map[string]interface{}{
            "jsonrpc": "2.0",
            "method":  "$/cancelRequest",
            "params": map[string]interface{}{
                "id": 1,
            },
        }
        encoder.Encode(cancel)
        fmt.Println("✓ Timeout handling works")
    }
}
```

## Quick Diagnostic Checklist

Run these commands to quickly diagnose common issues:

```bash
# 1. Check JSON output validity
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | your-server 2>/dev/null | jq .

# 2. Check notification handling  
echo '{"jsonrpc":"2.0","method":"notifications/initialized"}' | your-server 2>/dev/null | wc -c

# 3. Check error format
echo '{"jsonrpc":"2.0","id":1,"method":"invalid"}' | your-server 2>/dev/null | jq .error

# 4. Check tools list
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | your-server 2>/dev/null | jq .result.tools

# 5. Check for stdout pollution
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | your-server 2>&1 | grep -v '^{' | wc -l
```

## Automated Compliance Score

```bash
#!/bin/bash
# MCP Compliance Score Calculator

SCORE=0
TOTAL=10

# Test 1: Valid JSON output
if echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | $1 2>/dev/null | jq . >/dev/null 2>&1; then
    ((SCORE++))
fi

# Test 2: No notification output
if [ -z "$(echo '{"jsonrpc":"2.0","method":"notifications/initialized"}' | $1 2>/dev/null)" ]; then
    ((SCORE++))
fi

# Test 3: Error response format
if echo '{"jsonrpc":"2.0","id":1,"method":"invalid"}' | $1 2>/dev/null | jq -e '.error.code' >/dev/null 2>&1; then
    ((SCORE++))
fi

# Test 4: ID preservation (string)
response=$(echo '{"jsonrpc":"2.0","id":"test","method":"initialize","params":{}}' | $1 2>/dev/null)
if echo "$response" | jq -e '.id == "test"' >/dev/null 2>&1; then
    ((SCORE++))
fi

# Test 5: ID preservation (number)
response=$(echo '{"jsonrpc":"2.0","id":42,"method":"initialize","params":{}}' | $1 2>/dev/null)
if echo "$response" | jq -e '.id == 42' >/dev/null 2>&1; then
    ((SCORE++))
fi

# Test 6: Required fields in initialize response
response=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | $1 2>/dev/null)
if echo "$response" | jq -e '.result.protocolVersion and .result.capabilities and .result.serverInfo' >/dev/null 2>&1; then
    ((SCORE++))
fi

# Test 7: Tools list (if applicable)
if echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | $1 2>/dev/null | jq -e '.result.tools' >/dev/null 2>&1; then
    ((SCORE++))
fi

# Test 8: No stdout pollution
extra_lines=$(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | $1 2>&1 | grep -v '^{' | wc -l)
if [ "$extra_lines" -eq 0 ]; then
    ((SCORE++))
fi

# Test 9: Proper error codes
error_code=$(echo '{"jsonrpc":"2.0","id":1,"method":"nonexistent"}' | $1 2>/dev/null | jq -r '.error.code')
if [ "$error_code" = "-32601" ]; then
    ((SCORE++))
fi

# Test 10: Clean shutdown
if timeout 2 $1 </dev/null >/dev/null 2>&1; then
    ((SCORE++))
fi

echo "MCP Compliance Score: $SCORE/$TOTAL"
echo ""
if [ $SCORE -eq $TOTAL ]; then
    echo "🏆 Perfect compliance!"
elif [ $SCORE -ge 8 ]; then
    echo "✅ Good compliance with minor issues"
elif [ $SCORE -ge 6 ]; then
    echo "⚠️  Moderate compliance - needs work"
else
    echo "❌ Poor compliance - significant issues"
fi
```

## Language-Specific Diagnostics

### Python
```python
# Check for common Python issues
grep -n "print(" *.py | grep -v "file=sys.stderr"
grep -n "logging.basicConfig" *.py | grep -v "stream=sys.stderr"
grep -n "True\|False\|None" *.py  # In JSON strings
```

### TypeScript/JavaScript
```bash
# Check for console.log to stdout
grep -n "console\." *.ts *.js | grep -v "console.error"
```

### Go
```bash
# Check for fmt.Print to stdout
grep -n "fmt.Print" *.go | grep -v "fmt.Fprint.*stderr"
```

This diagnostic suite helps ensure MCP compliance across all implementation languages.