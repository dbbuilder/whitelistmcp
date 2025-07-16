# AWS Security Group MCP Server

## Overview
This Model Context Protocol (MCP) server enables LLM agents (like Claude) to manage AWS EC2 Security Group rules through a standardized interface. It provides tools for adding IP whitelist rules, listing existing rules, and testing AWS connectivity.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   LLM Agent     │────▶│   MCP Server     │────▶│  AWS EC2 API    │
│   (Claude)      │◀────│   (Node/Python)  │◀────│ Security Groups │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                         │
        │ JSON Request           │ Execute Script          │
        └────────────────────────┼─────────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │ add_sg_rule_json.py    │
                    └─────────────────────────┘
```

## Features

### Available Tools

1. **add_security_group_rule**
   - Add an IP address to a security group
   - Automatic description formatting
   - Duplicate rule detection
   - Input validation

2. **list_security_group_rules**
   - List all rules for a security group
   - Optional port filtering
   - Detailed rule information

3. **test_aws_connection**
   - Verify AWS credentials
   - List available security groups
   - Connection diagnostics

4. **validate_rule_parameters**
   - Validate IP address format
   - Validate port numbers
   - Pre-flight checks

## Installation

### Prerequisites
- Node.js 18+ or Python 3.8+
- AWS credentials with EC2 permissions
- MCP-compatible client (Claude Desktop)

### TypeScript/Node.js Setup
```bash
cd D:\dev2\awswhitelist2\mcp_server
npm install
npm run build
```

### Python Setup
```bash
cd D:\dev2\awswhitelist2\mcp_server
pip install -r requirements.txt
```

## Configuration

### Claude Desktop Configuration

1. **Locate Claude Desktop config file:**
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add the MCP server configuration:**

```json
{
  "mcpServers": {
    "aws-security-group": {
      "command": "node",
      "args": ["D:\\dev2\\awswhitelist2\\mcp_server\\build\\index.js"],
      "env": {
        "NODE_ENV": "production"
      }
    }
  }
}
```

Or for Python version:

```json
{
  "mcpServers": {
    "aws-security-group": {
      "command": "python",
      "args": ["D:\\dev2\\awswhitelist2\\mcp_server\\server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

3. **Restart Claude Desktop** to load the new server

## Usage Examples

### In Claude Desktop

Once configured, you can interact with the MCP server directly in Claude:

```
Human: Can you add my IP address 203.0.113.45 to the development security group sg-0f0df629567eb6344 
on port 8080? Use my username john_doe and call it WebApp.

Claude: I'll add your IP address to the security group for you.

[Calls add_security_group_rule tool with parameters]

Successfully added the security group rule:
- IP Address: 203.0.113.45/32
- Port: 8080
- Security Group: sg-0f0df629567eb6344 (whm-dev)
- Description: WebApp - 8080-auto-john_doe-20250711-1435

The rule has been added and you should now have access on port 8080.
```

### Tool Parameters

#### add_security_group_rule
```json
{
  "UserName": "john_doe",
  "UserIP": "203.0.113.45",
  "Port": "8080",
  "SecurityGroupID": "sg-0f0df629567eb6344",
  "ResourceName": "WebApp"
}
```

#### list_security_group_rules
```json
{
  "security_group_id": "sg-0f0df629567eb6344",
  "port": "8080"  // optional
}
```

#### validate_rule_parameters
```json
{
  "UserIP": "203.0.113.45",
  "Port": "8080"
}
```

## Development

### Project Structure
```
mcp_server/
├── index.ts              # TypeScript MCP server implementation
├── server.py            # Python MCP server implementation
├── package.json         # Node.js dependencies
├── requirements.txt     # Python dependencies
├── tsconfig.json        # TypeScript configuration
├── claude_desktop_config.json  # Example Claude config
└── README.md           # This file
```

### Building from Source

**TypeScript:**
```bash
npm install
npm run build
```

**Python:**
```bash
pip install -r requirements.txt
```

### Testing

**Manual Testing:**
```bash
# TypeScript version
node build/index.js

# Python version
python server.py
```

**With MCP Inspector:**
```bash
npx @modelcontextprotocol/inspector node build/index.js
```

## Security Considerations

1. **Credentials**: Currently uses hardcoded AWS credentials. For production:
   - Use environment variables
   - Implement AWS IAM roles
   - Use AWS SSO or temporary credentials

2. **Input Validation**: All inputs are validated before execution
   - IP address format checking
   - Port range validation (1-65535)
   - Security group ID format verification

3. **Access Control**: Consider implementing:
   - User authentication
   - Request logging
   - Rate limiting
   - Approval workflows

## Troubleshooting

### Common Issues

1. **"MCP server not found" in Claude**
   - Verify the path in claude_desktop_config.json
   - Ensure the server is built (for TypeScript)
   - Check file permissions

2. **"AWS credentials not found"**
   - Verify credentials in server code
   - Check AWS permissions
   - Test with AWS CLI first

3. **"Failed to add rule"**
   - Check if rule already exists
   - Verify security group ID
   - Ensure proper AWS permissions

### Debug Mode

Enable debug logging by setting environment variables:

```json
{
  "mcpServers": {
    "aws-security-group": {
      "command": "node",
      "args": ["D:\\dev2\\awswhitelist2\\mcp_server\\build\\index.js"],
      "env": {
        "NODE_ENV": "development",
        "DEBUG": "true"
      }
    }
  }
}
```

## API Reference

### MCP Protocol Implementation

The server implements the Model Context Protocol v0.5.0 with:
- Resource listing
- Tool discovery
- Tool execution
- Error handling

### Response Format

All tool responses follow this format:
```json
{
  "success": true|false,
  "message": "Human-readable message",
  "data": { /* tool-specific data */ },
  "error": "Error message if success is false"
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review AWS Security Group documentation
3. Consult MCP protocol documentation
4. Open an issue on the project repository