# MCP Compliance Checklist for Server Development

This comprehensive checklist helps developers ensure their MCP servers comply with all protocol requirements. It's language-agnostic and can be adapted to any programming language.

## 1. Transport Layer Compliance

### 1.1 Communication Channel
- [ ] **STDIO Transport**: Server reads from stdin and writes to stdout
- [ ] **Output Discipline**: ONLY JSON-RPC messages written to stdout
- [ ] **Error/Debug Output**: All non-protocol output directed to stderr or log files
- [ ] **No Extraneous Output**: Zero print/console statements to stdout
- [ ] **Stream Flushing**: Flush stdout after each response
- [ ] **Line-Based Protocol**: Each JSON-RPC message on a single line

### 1.2 Future Transport Support (Optional)
- [ ] **HTTP/SSE Support**: If implementing HTTP transport
- [ ] **Authentication**: OAuth 2.1 for HTTP transport only
- [ ] **Content Types**: Proper Content-Type headers for HTTP

## 2. JSON-RPC 2.0 Compliance

### 2.1 Message Structure
- [ ] **Version Field**: All messages include `"jsonrpc": "2.0"`
- [ ] **Valid JSON**: Every message is well-formed JSON
- [ ] **Required Fields**: All mandatory fields present based on message type

### 2.2 Request Handling
- [ ] **ID Field**: Accept both string and integer IDs
- [ ] **ID Uniqueness**: Track used IDs within session
- [ ] **Method Field**: String indicating the operation
- [ ] **Params Field**: Object or array (when present)

### 2.3 Response Generation
- [ ] **Matching IDs**: Response ID matches request ID exactly
- [ ] **Result XOR Error**: Either result or error field, never both
- [ ] **No Response for Notifications**: Return nothing for requests without ID

### 2.4 Error Responses
- [ ] **Standard Error Codes**:
  - `-32700`: Parse error
  - `-32600`: Invalid request
  - `-32601`: Method not found
  - `-32602`: Invalid params
  - `-32603`: Internal error
- [ ] **Error Structure**: `{code, message, data?}`
- [ ] **Descriptive Messages**: Clear error descriptions

### 2.5 Batch Support
- [ ] **Receive Batches**: MUST support receiving batch requests
- [ ] **Send Batches**: MAY support sending batch requests (optional)

## 3. Protocol Lifecycle

### 3.1 Initialization Sequence
- [ ] **Wait for Initialize**: No operations before initialization
- [ ] **Initialize Request Handler**: Implement `initialize` method
- [ ] **Protocol Version**: Support and declare protocol version
- [ ] **Capability Declaration**: Declare server capabilities
- [ ] **Server Info**: Provide name and version
- [ ] **Instructions**: Optional user-facing instructions

### 3.2 Initialized Notification
- [ ] **Handle Notification**: Process `initialized` notification
- [ ] **No Response**: Don't send response to notification
- [ ] **Mark Ready**: Server ready for operations after this

### 3.3 Shutdown
- [ ] **Graceful Shutdown**: Clean resource cleanup
- [ ] **Timeout Handling**: Implement request timeouts
- [ ] **Cancel Support**: Handle `$/cancelRequest` notifications

## 4. Core Methods Implementation

### 4.1 Required Methods
- [ ] **initialize**: Initialization handshake
- [ ] **notifications/initialized**: Handle ready notification

### 4.2 Discovery Methods (Based on Capabilities)
- [ ] **tools/list**: If server provides tools
- [ ] **resources/list**: If server provides resources
- [ ] **prompts/list**: If server provides prompts

### 4.3 Execution Methods (Based on Capabilities)
- [ ] **tools/call**: Execute tool with parameters
- [ ] **resources/read**: Read resource content
- [ ] **prompts/get**: Get prompt template

## 5. Capability-Specific Requirements

### 5.1 Tools Capability
- [ ] **Tool Naming**: Use underscores, not slashes (e.g., `tool_name`)
- [ ] **Tool Description**: Clear, concise descriptions
- [ ] **Input Schema**: Valid JSON Schema Draft 7
- [ ] **Schema Validation**: Validate inputs against schema
- [ ] **Error Handling**: Return appropriate errors for invalid inputs

### 5.2 Resources Capability
- [ ] **Resource URIs**: Proper URI formatting
- [ ] **Resource Types**: Declare MIME types
- [ ] **Content Delivery**: Efficient content streaming
- [ ] **Access Control**: Validate resource access

### 5.3 Prompts Capability
- [ ] **Prompt Structure**: Well-defined prompt templates
- [ ] **Parameter Handling**: Accept and validate arguments
- [ ] **Template Rendering**: Proper variable substitution

## 6. JSON Schema Compliance

### 6.1 Schema Structure
- [ ] **Draft 7 Compliance**: Use JSON Schema Draft 7
- [ ] **Type Definitions**: All properties have types
- [ ] **Required Arrays**: `required` at object level, not in properties
- [ ] **Consistent Schemas**: Reuse common schemas (e.g., credentials)

### 6.2 Schema Constraints
- [ ] **Numeric Bounds**: min/max for integers
- [ ] **String Patterns**: Regex patterns where appropriate
- [ ] **Enumerations**: Use `enum` for fixed value sets
- [ ] **Descriptions**: All fields have descriptions

### 6.3 Common Pitfalls to Avoid
- [ ] **No `required` in Properties**: Never `"required": false` inside property
- [ ] **Proper Boolean Format**: Use `true/false`, not `True/False`
- [ ] **No Python None**: Use `null`, not `None`
- [ ] **Double Quotes**: JSON requires double quotes

## 7. State Management

### 7.1 Stateless Design
- [ ] **No Session State**: Each request self-contained
- [ ] **Credential Handling**: Never store credentials
- [ ] **Request Independence**: Requests don't depend on previous requests

### 7.2 Connection State
- [ ] **Initialization State**: Track if initialized
- [ ] **Capability State**: Remember declared capabilities
- [ ] **Request Tracking**: Track active request IDs

## 8. Performance and Reliability

### 8.1 Timeout Management
- [ ] **Request Timeouts**: Implement configurable timeouts
- [ ] **Progress Notifications**: Send `$/progress` for long operations
- [ ] **Cancellation**: Support `$/cancelRequest`

### 8.2 Resource Management
- [ ] **Memory Limits**: Prevent memory exhaustion
- [ ] **Connection Limits**: Manage concurrent operations
- [ ] **Clean Cleanup**: Release resources properly

## 9. Security Considerations

### 9.1 Input Validation
- [ ] **Parameter Validation**: Validate all inputs
- [ ] **Injection Prevention**: Sanitize inputs
- [ ] **Path Traversal**: Prevent directory traversal attacks

### 9.2 Credential Security
- [ ] **No Storage**: Never persist credentials
- [ ] **Secure Transmission**: Use secure channels
- [ ] **Minimal Scope**: Request minimal permissions

## 10. Testing and Validation

### 10.1 Protocol Testing
- [ ] **Valid Responses**: Test with actual MCP client
- [ ] **Error Cases**: Test all error conditions
- [ ] **Edge Cases**: Test boundary conditions

### 10.2 Compliance Testing
- [ ] **Claude Desktop**: Test with Claude Desktop
- [ ] **Schema Validation**: Validate all schemas
- [ ] **Output Cleanliness**: Verify stdout contains only JSON-RPC

## Implementation Guide by Language

### For Python Implementations
```python
# Check for:
- No print() to stdout
- Logging to stderr only
- Proper JSON serialization
- Type hints matching schema
```

### For TypeScript/JavaScript
```typescript
// Check for:
// - No console.log() to stdout
// - Proper async/await handling
// - Type definitions matching schema
// - JSON.stringify for output
```

### For Go Implementations
```go
// Check for:
// - No fmt.Println() to stdout
// - Proper JSON marshaling
// - Interface compliance
// - Error handling patterns
```

### For Rust Implementations
```rust
// Check for:
// - No println!() to stdout
// - Serde compliance
// - Result<T, E> error handling
// - Lifetime management
```

## Quick Validation Script

```bash
# Test basic compliance
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' | your-server

# Should return valid JSON with capabilities
# Should NOT output anything else to stdout
```

## Common Failures and Fixes

1. **"Unexpected end of JSON input"**
   - Check: No debug output to stdout
   - Check: Proper notification handling
   - Check: JSON validity

2. **"Method not found"**
   - Check: Method routing implementation
   - Check: Method name format (underscores)
   - Check: Initialization sequence

3. **"Invalid params"**
   - Check: Schema compliance
   - Check: Required fields
   - Check: Type matching

4. **"String should match pattern"**
   - Check: Tool naming (use underscores)
   - Check: Schema format
   - Check: Enum values

## Final Checklist

- [ ] **README**: Document MCP compatibility
- [ ] **Examples**: Provide usage examples
- [ ] **Testing**: Automated compliance tests
- [ ] **Versioning**: Follow semantic versioning
- [ ] **Changelog**: Document breaking changes