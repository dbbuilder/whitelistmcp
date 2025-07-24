# Building MCP Servers with Python: A Complete Guide to Protocol Compliance

## Introduction

The Model Context Protocol (MCP) is a powerful way to extend AI assistants like Claude Desktop with custom tools. However, building an MCP server requires strict adherence to protocol specifications, particularly around input/output streams, JSON schema validation, and naming conventions. This guide documents critical lessons learned while building the `whitelistmcp-mcp` server (versions 1.0.0 through 1.1.9) and provides best practices for Python developers.

## The Fundamental Rule of MCP

**MCP servers communicate via stdin/stdout using JSON-RPC 2.0 protocol. ONLY valid JSON-RPC messages should ever be written to stdout.**

This simple rule has profound implications that can trip up Python developers accustomed to using `print()` for debugging or logging.

## Understanding stdin, stdout, and stderr

### What are these streams?

- **stdin (Standard Input)**: Where your program receives input
- **stdout (Standard Output)**: Where your program sends its primary output
- **stderr (Standard Error)**: Where your program sends error messages and diagnostics

### Why MCP cares about stdout

MCP uses stdout as a structured communication channel. When Claude Desktop starts your MCP server, it:
1. Sends JSON-RPC requests to your server's stdin
2. Reads JSON-RPC responses from your server's stdout
3. Expects EVERY line on stdout to be valid JSON

Any non-JSON output to stdout breaks this contract and causes errors.

## Common Pitfalls and Solutions

### Pitfall 1: Logging to stdout

**Problem:**
```python
import logging

# This creates a handler that outputs to stdout by default!
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_request(request):
    logger.info(f"Processing request: {request}")  # Goes to stdout!
    return {"result": "success"}
```

**What happens:** Your log messages appear on stdout, Claude Desktop tries to parse them as JSON, and you get "Unexpected end of JSON input" errors.

**Solution:**
```python
import sys
import logging

# Always explicitly send logs to stderr
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Ensure no propagation to root logger which might have stdout handlers
logger.propagate = False
```

### Pitfall 2: Debug print statements

**Problem:**
```python
def process_request(request):
    print(f"Debug: Got request {request}")  # Goes to stdout!
    result = do_something(request)
    print(f"Debug: Result is {result}")     # Goes to stdout!
    return json.dumps({"result": result})
```

**Solution:**
```python
import sys

def process_request(request):
    print(f"Debug: Got request {request}", file=sys.stderr)  # Goes to stderr
    result = do_something(request)
    print(f"Debug: Result is {result}", file=sys.stderr)     # Goes to stderr
    return json.dumps({"result": result})
```

### Pitfall 3: Handling MCP notifications

**Problem:**
```python
def handle_request(request):
    if request.get("id") is None:
        # It's a notification - no response needed
        return ""  # Empty string is not valid JSON!
```

**What happens:** MCP notifications (like `notifications/initialized`) don't have an `id` field because they don't expect responses. However, if your server prints an empty string to stdout, Claude Desktop still tries to parse it as JSON and fails.

**Solution:**
```python
def handle_request(request):
    if request.get("id") is None:
        # It's a notification - return None to indicate no response
        return None

# In your main loop:
def run_server():
    for line in sys.stdin:
        request = json.loads(line.strip())
        response = handle_request(request)
        
        # Only print if there's an actual response
        if response is not None:
            print(response)
            sys.stdout.flush()
```

### Pitfall 4: Library output pollution

**Problem:** Some libraries (especially in scientific Python) print progress messages, warnings, or results directly to stdout.

**Solution:**
```python
import sys
import os
from contextlib import redirect_stdout

# Option 1: Redirect stdout for specific operations
with redirect_stdout(sys.stderr):
    # Any prints here go to stderr
    problematic_library.do_something()

# Option 2: Silence stdout completely during imports
old_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')
import noisy_library
sys.stdout = old_stdout

# Option 3: Configure libraries to be quiet
import warnings
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Example for TensorFlow
```

## MCP Protocol Essentials

### Request Types

1. **Regular Requests** (have an `id` field):
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "initialize",
     "params": {}
   }
   ```
   **Requirement:** Must respond with a JSON-RPC response containing the same `id`.

2. **Notifications** (no `id` field):
   ```json
   {
     "jsonrpc": "2.0",
     "method": "notifications/initialized"
   }
   ```
   **Requirement:** Must NOT send any response.

### Complete Python MCP Server Template

```python
#!/usr/bin/env python3
"""Template for a compliant MCP server."""

import sys
import json
import logging
from typing import Dict, Any, Optional

# Set up logging to stderr ONLY
def setup_logging():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    logger = logging.getLogger('mcp_server')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Don't propagate to root logger
    
    return logger

logger = setup_logging()

def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle a single MCP request.
    
    Returns:
        Dict for regular requests (will be serialized to JSON)
        None for notifications (no response needed)
    """
    request_id = request.get("id")
    method = request.get("method", "")
    
    # Check if this is a notification (no id field)
    if request_id is None:
        logger.info(f"Received notification: {method}")
        # Notifications get no response
        return None
    
    logger.info(f"Processing request {request_id}: {method}")
    
    # Handle different methods
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {
                    "name": "example-server",
                    "version": "1.0.0"
                }
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": []  # Your tools here
            }
        }
    else:
        # Method not found
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

def main():
    """Run the MCP server."""
    logger.info("MCP server starting")
    
    try:
        # Read from stdin line by line
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse request
                request = json.loads(line)
                
                # Handle request
                response = handle_request(request)
                
                # Send response ONLY if not None
                if response is not None:
                    print(json.dumps(response))
                    sys.stdout.flush()
                    
            except json.JSONDecodeError as e:
                # Send error response for parse errors
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                        "data": str(e)
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
            except Exception as e:
                logger.exception("Unexpected error processing request")
                # Don't send internal errors to stdout unless we have a request ID
                
    except KeyboardInterrupt:
        logger.info("Server interrupted")
    except Exception as e:
        logger.exception("Server error")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Best Practices Checklist

✅ **NEVER use plain `print()` in production MCP code** - Always use `print(..., file=sys.stderr)` for debugging

✅ **Configure logging to use stderr exclusively** - Set up handlers explicitly, don't rely on defaults

✅ **Handle notifications properly** - Return `None` and skip stdout output entirely

✅ **Test with real MCP clients** - Use tools like Claude Desktop to verify protocol compliance

✅ **Validate all stdout output** - Every line printed to stdout must be valid JSON-RPC

✅ **Handle errors gracefully** - Send proper JSON-RPC error responses, don't let exceptions leak to stdout

✅ **Flush stdout after responses** - Use `sys.stdout.flush()` to ensure immediate delivery

✅ **Silence noisy libraries** - Redirect or suppress any library output to stdout

## Testing Your MCP Server

### Simple Protocol Test
```bash
# This should return ONLY valid JSON
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python your_server.py

# This should return NOTHING (it's a notification)
echo '{"jsonrpc":"2.0","method":"notifications/initialized"}' | python your_server.py
```

### Debugging Tips

1. **Separate stdout and stderr during testing:**
   ```bash
   # See only stdout (should be pure JSON)
   python your_server.py < test_input.json 2>/dev/null
   
   # See only stderr (logs and debug info)
   python your_server.py < test_input.json 2>&1 1>/dev/null
   ```

2. **Validate JSON output:**
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | \
   python your_server.py 2>/dev/null | \
   jq .
   ```

3. **Use environment variables for debugging:**
   ```python
   import os
   
   # Only enable debug output when explicitly requested
   if os.environ.get('MCP_DEBUG'):
       logger.setLevel(logging.DEBUG)
   ```

## Conclusion

Building MCP servers in Python requires discipline about output streams. The golden rule is simple: **stdout is for JSON-RPC only**. Everything else—logs, debug output, errors—must go to stderr or be suppressed entirely.

By following these guidelines, you can avoid the common pitfalls that lead to "Unexpected end of JSON input" and other protocol errors, ensuring your MCP server works reliably with Claude Desktop and other MCP clients.

## Additional Lessons from whitelistmcp-mcp Development

### Version Management (v1.1.7)

**Problem:** Version displayed incorrectly when running `--version` command.

**Solution:** Centralize version management in a single file:

```python
# __version__.py
"""Version information for your package."""
__version__ = "1.1.9"

# setup.py
exec(open("your_package/__version__.py").read())

# main.py or cli.py
from your_package import __version__
parser.add_argument('--version', action='version', version=__version__)
```

### JSON Schema Validation (v1.1.8)

**Problem:** Claude Desktop shows "string should match pattern" errors for tool definitions.

**Common Issues:**

1. **Invalid schema properties:**
   ```json
   // WRONG - "required" can't be inside a property definition
   {
     "session_token": {
       "type": "string",
       "required": false  // This is invalid!
     }
   }
   
   // CORRECT - "required" is an array at the object level
   {
     "properties": {
       "session_token": {"type": "string"}
     },
     "required": ["other_field"]  // session_token is optional
   }
   ```

2. **Inconsistent schemas across tools:**
   ```python
   # GOOD - Define reusable schemas
   credential_schema = {
       "type": "object",
       "properties": {
           "access_key_id": {"type": "string"},
           "secret_access_key": {"type": "string"},
           "region": {"type": "string"},
           "session_token": {"type": "string"}
       },
       "required": ["access_key_id", "secret_access_key", "region"]
   }
   
   # Use the same schema everywhere
   tools = [
       {
           "name": "tool1",
           "inputSchema": {
               "properties": {
                   "credentials": credential_schema,
                   # ... other properties
               }
           }
       }
   ]
   ```

3. **Missing constraints on fields:**
   ```json
   // GOOD - Add constraints for better validation
   {
     "port": {
       "type": "integer",
       "description": "Port number",
       "minimum": 1,
       "maximum": 65535
     },
     "protocol": {
       "type": "string",
       "enum": ["tcp", "udp", "icmp"],
       "description": "Network protocol"
     }
   }
   ```

### Tool Naming Conventions (v1.1.9)

**Problem:** Tool names with slashes (e.g., `whitelist/add`) cause validation errors.

**Solution:** Use underscores instead of slashes:

```python
# WRONG
tools = [
    {"name": "namespace/action", ...}
]

# CORRECT
tools = [
    {"name": "namespace_action", ...}
]

# Update your method routing to match
self.methods = {
    "namespace_action": self._handle_namespace_action,
    # ...
}
```

### ID Field Flexibility (v1.1.1)

**Problem:** JSON-RPC id field can be string or number, but strict type checking causes crashes.

**Solution:** Accept both types:

```python
from typing import Union

class MCPRequest(BaseModel):
    jsonrpc: str
    id: Optional[Union[str, int]] = None  # Can be string, int, or None
    method: str
    params: Dict[str, Any] = {}
```

### Windows-Specific Issues

**Problem:** Even stderr output can cause issues on Windows in some configurations.

**Solution:** Make logging completely optional:

```python
import os

# Only enable logging if explicitly requested
if os.environ.get('MCP_ENABLE_LOGGING'):
    # Set up logging
    pass
else:
    # Disable all logging
    logging.disable(logging.CRITICAL)
```

## Complete Best Practices Checklist

✅ **Output Stream Discipline**
- NEVER use plain `print()` in production MCP code
- Configure logging to use stderr exclusively
- Consider disabling console logging entirely for maximum compatibility

✅ **Protocol Compliance**
- Handle notifications properly (return `None`, no stdout output)
- Accept flexible id types (string or number)
- Implement all required methods (`initialize`, `tools/list`, etc.)

✅ **JSON Schema Validation**
- Use JSON Schema Draft 7 format
- Define reusable schemas for common structures
- Add proper constraints (min/max, enum, etc.)
- Never put `"required"` inside property definitions

✅ **Tool Naming**
- Use underscores, not slashes (e.g., `tool_name` not `tool/name`)
- Keep names consistent between definition and method routing
- Use descriptive names that indicate the action

✅ **Version Management**
- Centralize version in `__version__.py`
- Reference it consistently across all files
- Update version with each release

✅ **Error Handling**
- Send proper JSON-RPC error responses
- Use appropriate error codes (-32600, -32601, etc.)
- Include helpful error messages and data

✅ **Testing**
- Test with real MCP clients (Claude Desktop)
- Validate all JSON schemas
- Check stdout contains only valid JSON-RPC
- Test both regular requests and notifications

## Debugging Workflow

1. **Enable verbose logging to a file:**
   ```python
   if os.environ.get('MCP_DEBUG'):
       file_handler = logging.FileHandler('/tmp/mcp_debug.log')
       logger.addHandler(file_handler)
   ```

2. **Test individual components:**
   ```bash
   # Test stdout cleanliness
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
   python -m your_server 2>/dev/null | jq .
   ```

3. **Validate schemas:**
   ```python
   from jsonschema import Draft7Validator
   
   # Validate your tool schemas
   for tool in tools:
       Draft7Validator.check_schema(tool["inputSchema"])
   ```

## Version History Lessons

- **v1.0.1**: Initial stdout/stderr separation
- **v1.1.1**: ID field type flexibility
- **v1.1.5**: Complete console logging disable
- **v1.1.6**: Notification handling fix
- **v1.1.7**: Centralized version management
- **v1.1.8**: JSON schema validation fixes
- **v1.1.9**: Tool naming convention change

## Further Reading

- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [JSON Schema Draft 7](https://json-schema.org/draft-07/json-schema-release-notes.html)
- [Python logging documentation](https://docs.python.org/3/library/logging.html)
- [Python stdin, stdout, stderr](https://docs.python.org/3/library/sys.html#sys.stdin)