# AWS Whitelist MCP Server

[![PyPI version](https://badge.fury.io/py/awswhitelist-mcp.svg)](https://pypi.org/project/awswhitelist-mcp/)
[![Python versions](https://img.shields.io/pypi/pyversions/awswhitelist-mcp.svg)](https://pypi.org/project/awswhitelist-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.1.10-blue.svg)](https://modelcontextprotocol.io)

A Model Context Protocol (MCP) server for managing AWS EC2 Security Group rules. Fully compatible with Claude Desktop and other MCP clients.

## 🚀 Features

- **MCP Protocol Compliance**: Full JSON-RPC 2.0 implementation with batch support
- **Claude Desktop Integration**: Seamless integration with Claude for AWS management
- **Stateless Design**: No credential storage - secure by design
- **Tool-based Interface**: Add, remove, list, and check IP whitelist rules
- **Flexible Credential Management**: Environment variables, AWS profiles, or per-request
- **Comprehensive Validation**: IP address, port, and parameter validation
- **Production Ready**: Error handling, logging, and timeout management

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install awswhitelist-mcp>=1.1.10
```

### From Source

```bash
git clone https://github.com/dbbuilder/awswhitelist2.git
cd awswhitelist2
pip install -e .

```

## 🔧 Quick Start

### 1. Install the Server

```bash
pip install awswhitelist-mcp>=1.1.10
```

### 2. Configure Claude Desktop

Add to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "env": {
        "AWS_ACCESS_KEY_ID": "your-key",
        "AWS_SECRET_ACCESS_KEY": "your-secret",
        "AWS_DEFAULT_REGION": "us-east-1"
      }
    }
  }
}
```

### 3. Use in Claude

Simply ask Claude to manage your security groups:
- "Add my IP to security group sg-123456 for SSH access"
- "List all rules in security group sg-123456"
- "Remove IP 192.168.1.1 from security group sg-123456"

For detailed setup instructions, see [CLAUDE_DESKTOP_SETUP.md](CLAUDE_DESKTOP_SETUP.md).

## 🔐 Environment Variables

Key environment variables (see `.env.example` for full list):

```env
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1

# Default Security Group
DEFAULT_SECURITY_GROUP_ID=sg-0f0df629567eb6344
DEFAULT_SECURITY_GROUP_NAME=whm-dev

# Description Format
DESCRIPTION_PREFIX=auto
DESCRIPTION_SEPARATOR=-
DESCRIPTION_TIMESTAMP_FORMAT=%Y%m%d-%H%M
```

## 🛠️ Available Tools

The MCP server provides these tools:

### `whitelist_add`
Add an IP address to a security group.

```json
{
  "credentials": {...},
  "security_group_id": "sg-123456",
  "ip_address": "192.168.1.1",
  "port": 22,
  "protocol": "tcp",
  "description": "SSH access"
}
```

### `whitelist_remove`
Remove an IP address from a security group.

### `whitelist_list`
List all rules in a security group.

### `whitelist_check`
Check if an IP address is whitelisted.

In Claude Desktop, these appear as:
- `awswhitelist:whitelist_add`
- `awswhitelist:whitelist_remove`
- `awswhitelist:whitelist_list`
- `awswhitelist:whitelist_check`

## 🔐 Credential Management

### Option 1: Environment Variables
```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "env": {
        "AWS_ACCESS_KEY_ID": "your-key",
        "AWS_SECRET_ACCESS_KEY": "your-secret",
        "AWS_DEFAULT_REGION": "us-east-1"
      }
    }
  }
}
```

### Option 2: AWS Profile
```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "env": {
        "AWS_PROFILE": "production"
      }
    }
  }
}
```

### Option 3: Per-Request
Claude will prompt for credentials when needed.

For advanced patterns, see [MCP_CREDENTIAL_PATTERNS.md](MCP_CREDENTIAL_PATTERNS.md).

## 🛡️ Security Best Practices

1. **Never store credentials in config files**
2. **Use IAM roles** when running on AWS infrastructure
3. **Rotate credentials** regularly
4. **Minimal permissions** - Only grant required EC2 permissions:
   - `ec2:DescribeSecurityGroups`
   - `ec2:AuthorizeSecurityGroupIngress`
   - `ec2:RevokeSecurityGroupIngress`

## 🧪 Testing

### Test the MCP Server

```bash
# Test initialization
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{}}' | awswhitelist

# List available tools
echo '{"jsonrpc":"2.0","method":"tools/list","id":2,"params":{}}' | awswhitelist
```

### Run Compliance Tests

```bash
# Check MCP compliance
python MCP_DIAGNOSTIC_SCRIPT.py awswhitelist
```

## 🔍 Troubleshooting

### Common Issues

1. **"Method not found: tools/call"**
   - Update to version 1.1.10 or later
   - Restart Claude Desktop

2. **"Unexpected end of JSON input"**
   - Update to version 1.1.6 or later
   - Check for debug output to stdout

3. **AWS credentials error:**
   - Verify environment variables are set
   - Test with: `aws sts get-caller-identity`

4. **Permission denied:**
   - Ensure IAM user has required EC2 permissions
   - Check security group exists in the correct region

### Enable Debug Logging

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "args": ["-v"]
    }
  }
}
```

## 📚 MCP Protocol Compliance

This server implements:
- ✅ JSON-RPC 2.0 protocol
- ✅ Batch request support
- ✅ Standard `tools/call` method
- ✅ Request ID tracking
- ✅ Proper notification handling
- ✅ Comprehensive error codes

For compliance details, see:
- [MCP_COMPLIANCE_CHECKLIST.md](MCP_COMPLIANCE_CHECKLIST.md)
- [MCP_COMPLIANCE_REPORT.md](MCP_COMPLIANCE_REPORT.md)

## 📖 Documentation

- [CLAUDE_DESKTOP_SETUP.md](CLAUDE_DESKTOP_SETUP.md) - Detailed Claude Desktop setup
- [MCP_CREDENTIAL_PATTERNS.md](MCP_CREDENTIAL_PATTERNS.md) - Credential management patterns
- [MCP_COMPLIANCE_CHECKLIST.md](MCP_COMPLIANCE_CHECKLIST.md) - MCP development guide
- [MCP_PYTHON_STDOUT_GUIDE.md](MCP_PYTHON_STDOUT_GUIDE.md) - Python MCP best practices

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run compliance tests
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🏷️ Version History

- **v1.1.10** - Added `tools/call` support and batch requests
- **v1.1.9** - Updated tool naming convention
- **v1.1.8** - Fixed JSON schema validation
- **v1.1.7** - Centralized version management
- **v1.1.6** - Fixed notification handling

See [CHANGELOG.md](CHANGELOG.md) for full history.