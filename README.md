# Multi-Cloud Whitelist MCP Server

[![PyPI version](https://badge.fury.io/py/whitelistmcp.svg)](https://pypi.org/project/whitelistmcp/)
[![Python versions](https://img.shields.io/pypi/pyversions/whitelistmcp.svg)](https://pypi.org/project/whitelistmcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.1.10-blue.svg)](https://modelcontextprotocol.io)
[![AWS](https://img.shields.io/badge/AWS-Supported-FF9900.svg)](https://aws.amazon.com/)
[![Azure](https://img.shields.io/badge/Azure-Supported-0078D4.svg)](https://azure.microsoft.com/)
[![GCP](https://img.shields.io/badge/GCP-Supported-4285F4.svg)](https://cloud.google.com/)

A Model Context Protocol (MCP) server for managing security group/firewall rules across AWS, Azure, and Google Cloud Platform. Provides unified whitelisting capabilities with cloud-specific optimizations and parallel processing.

## 🚀 Features

### Core Features
- **Multi-Cloud Support**: Unified interface for AWS, Azure, and GCP firewall management
- **MCP Protocol Compliance**: Full JSON-RPC 2.0 implementation with batch support
- **Claude Desktop Integration**: Seamless integration with Claude for multi-cloud management
- **Stateless Design**: No credential storage - secure by design
- **Parallel Processing**: Execute operations across multiple clouds simultaneously
- **Comprehensive Validation**: IP address, port, and parameter validation
- **Production Ready**: Error handling, logging, and timeout management

### Cloud-Specific Features
- **AWS**: EC2 Security Groups with full rule management
- **Azure**: Network Security Groups with priority-based rules
- **GCP**: VPC Firewall Rules with additive-only mode for safety

### Advanced Removal Options
- Remove by IP address only (across all ports/services)
- Remove by service name/port only (across all IPs)
- Remove by IP + service name/port combination
- Bulk removal operations with filtering

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install whitelistmcp>=2.0.0
```

### From Source

```bash
git clone https://github.com/dbbuilder/whitelistmcp.git
cd whitelistmcp
pip install -e .
```

## 🔧 Quick Start

### 1. Install the Server

```bash
pip install whitelistmcp>=2.0.0
```

### 2. Configure Claude Desktop

Add to your Claude Desktop configuration file:

```json
{
  "mcpServers": {
    "whitelistmcp": {
      "command": "whitelistmcp",
      "env": {
        "CLOUD_PROVIDER": "aws",  // Options: aws, azure, gcp, all
        "AWS_ACCESS_KEY_ID": "your-aws-key",
        "AWS_SECRET_ACCESS_KEY": "your-aws-secret",
        "AWS_DEFAULT_REGION": "us-east-1",
        "AZURE_CLIENT_ID": "your-azure-client-id",
        "AZURE_CLIENT_SECRET": "your-azure-secret",
        "AZURE_TENANT_ID": "your-azure-tenant",
        "AZURE_SUBSCRIPTION_ID": "your-azure-subscription",
        "GCP_PROJECT_ID": "your-gcp-project",
        "GCP_CREDENTIALS_PATH": "/path/to/gcp-credentials.json"
      }
    }
  }
}
```

### 3. Use in Claude

Simply ask Claude to manage your security groups across any cloud:
- "Add my IP to AWS security group sg-123456 for SSH access"
- "Add 192.168.1.0/24 to Azure NSG web-nsg for HTTPS"
- "Add my IP to GCP firewall for port 8080" (additive-only for safety)
- "Remove IP 192.168.1.1 from all security groups"
- "Remove all SSH rules from security group sg-123456"
- "Remove 192.168.1.1:443 from Azure NSG"

For detailed setup instructions, see [CLAUDE_DESKTOP_SETUP.md](docs/CLAUDE_DESKTOP_SETUP.md).

## 🔐 Environment Variables

Key environment variables (see `.env.example` for full list):

```env
# Cloud Provider Selection
CLOUD_PROVIDER=aws  # Options: aws, azure, gcp, all

# AWS Credentials
AWS_ACCESS_KEY_ID=your_aws_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_here
AWS_DEFAULT_REGION=us-east-1
AWS_DEFAULT_SECURITY_GROUP_ID=sg-0f0df629567eb6344

# Azure Credentials
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=your_azure_tenant_id
AZURE_SUBSCRIPTION_ID=your_azure_subscription_id
AZURE_DEFAULT_RESOURCE_GROUP=my-resource-group
AZURE_DEFAULT_NSG_NAME=my-nsg

# GCP Credentials
GCP_PROJECT_ID=your_gcp_project
GCP_CREDENTIALS_PATH=/path/to/credentials.json
GCP_DEFAULT_NETWORK=default
GCP_ADDITIVE_ONLY=true  # Safety feature: only add rules, never remove

# Common Settings
DESCRIPTION_PREFIX=auto
DESCRIPTION_SEPARATOR=-
DESCRIPTION_TIMESTAMP_FORMAT=%Y%m%d-%H%M
```

## 🛠️ Available Tools

The MCP server provides these tools:

### `whitelist_add`
Add an IP address to a security group/firewall.

```json
{
  "cloud": "aws",  // aws, azure, or gcp
  "credentials": {...},
  "security_group_id": "sg-123456",  // or nsg_name for Azure, firewall_name for GCP
  "ip_address": "192.168.1.1",
  "port": 22,
  "protocol": "tcp",
  "description": "SSH access",
  "service_name": "ssh"  // optional: for service-based rules
}
```

### `whitelist_remove`
Remove rules with flexible filtering:
- By IP only: removes all rules for that IP
- By service/port only: removes all rules for that service
- By IP + service/port: removes specific combination

```json
{
  "cloud": "aws",
  "credentials": {...},
  "security_group_id": "sg-123456",
  "ip_address": "192.168.1.1",  // optional
  "port": 22,  // optional
  "service_name": "ssh"  // optional
}
```

### `whitelist_list`
List all rules in a security group/firewall.

### `whitelist_check`
Check if an IP/service combination is whitelisted.

### `whitelist_sync`
Synchronize rules across multiple clouds (Enterprise feature).

In Claude Desktop, these appear as:
- `whitelistmcp:whitelist_add`
- `whitelistmcp:whitelist_remove`
- `whitelistmcp:whitelist_list`
- `whitelistmcp:whitelist_check`
- `whitelistmcp:whitelist_sync`

## 🔐 Credential Management

### Option 1: Environment Variables
```json
{
  "mcpServers": {
    "whitelistmcp": {
      "command": "whitelistmcp",
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
    "whitelistmcp": {
      "command": "whitelistmcp",
      "env": {
        "AWS_PROFILE": "production"
      }
    }
  }
}
```

### Option 3: Per-Request
Claude will prompt for credentials when needed.

For advanced patterns, see [MCP_CREDENTIAL_PATTERNS.md](docs/MCP_CREDENTIAL_PATTERNS.md).

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
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{}}' | whitelistmcp

# List available tools
echo '{"jsonrpc":"2.0","method":"tools/list","id":2,"params":{}}' | whitelistmcp
```

### Run Compliance Tests

```bash
# Check MCP compliance
python MCP_DIAGNOSTIC_SCRIPT.py whitelistmcp
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
    "whitelistmcp": {
      "command": "whitelistmcp",
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
- [MCP_COMPLIANCE_CHECKLIST.md](docs/MCP_COMPLIANCE_CHECKLIST.md)
- [MCP_COMPLIANCE_REPORT.md](docs/MCP_COMPLIANCE_REPORT.md)

## 📖 Documentation

- [CLAUDE_DESKTOP_SETUP.md](docs/CLAUDE_DESKTOP_SETUP.md) - Detailed Claude Desktop setup
- [MCP_CREDENTIAL_PATTERNS.md](docs/MCP_CREDENTIAL_PATTERNS.md) - Credential management patterns
- [MCP_COMPLIANCE_CHECKLIST.md](docs/MCP_COMPLIANCE_CHECKLIST.md) - MCP development guide
- [MCP_PYTHON_STDOUT_GUIDE.md](docs/MCP_PYTHON_STDOUT_GUIDE.md) - Python MCP best practices

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