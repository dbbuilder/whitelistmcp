# Claude Desktop Setup Guide

This guide explains how to install and configure the AWS Whitelisting MCP Server for use with Claude Desktop.

## Installation Options

### Option 1: Install from PyPI (Recommended)

1. Install the package (version 1.1.10 or later required):
   ```bash
   pip install awswhitelist-mcp>=1.1.10
   ```

2. Add to Claude Desktop configuration:
   ```json
   {
     "mcpServers": {
       "awswhitelist": {
         "command": "awswhitelist",
         "args": [],
         "env": {
           "PYTHONUNBUFFERED": "1"
         }
       }
     }
   }
   ```

### Option 2: Run from Source Directory

1. Clone the repository:
   ```bash
   git clone https://github.com/dbbuilder/awswhitelist2.git
   cd awswhitelist2
   pip install -r requirements.txt
   ```

2. Add to Claude Desktop configuration:
   ```json
   {
     "mcpServers": {
       "awswhitelist": {
         "command": "python",
         "args": ["-m", "awswhitelist.main"],
         "cwd": "/full/path/to/awswhitelist2",
         "env": {
           "PYTHONUNBUFFERED": "1",
           "PYTHONPATH": "/full/path/to/awswhitelist2"
         }
       }
     }
   }
   ```

### Option 3: Run with Configuration File

If you want to use a configuration file for default settings:

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "args": ["-c", "/path/to/config.json"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

## Configuration File (Optional)

Create a configuration file to set defaults:

```json
{
  "default_parameters": {
    "region": "us-east-1",
    "port": 443,
    "protocol": "tcp",
    "description_template": "MCP whitelisted {ip} on {date}"
  },
  "security_settings": {
    "max_rules_per_request": 10,
    "allowed_ports": [22, 80, 443, 3306, 5432],
    "allowed_protocols": ["tcp", "udp"],
    "require_description": true
  }
}
```

## Claude Desktop Configuration Location

The Claude Desktop configuration file is typically located at:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

## Usage in Claude Desktop

Once configured, you can use the MCP server in Claude by making requests like:

```
Add my current IP to security group sg-123456789 for HTTPS access
```

Claude will use the MCP tools with the following format:
- Tool names appear as `awswhitelist:whitelist_add` in Claude Desktop
- The server implements the standard `tools/call` method for execution

## Available Tools

The server provides these MCP tools:

1. **whitelist_add** - Add an IP to a security group
2. **whitelist_remove** - Remove an IP from a security group
3. **whitelist_list** - List all rules in a security group
4. **whitelist_check** - Check if an IP is whitelisted

In Claude Desktop, these appear with the server prefix:
- `awswhitelist:whitelist_add`
- `awswhitelist:whitelist_remove`
- `awswhitelist:whitelist_list`
- `awswhitelist:whitelist_check`

## Security Notes

- AWS credentials are passed with each request (stateless)
- Never store credentials in configuration files
- Claude Desktop will handle credential prompting
- Consider using AWS IAM roles or temporary credentials

### Credential Management Options

1. **Environment Variables** (Recommended for development):
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

2. **AWS Profile**:
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

3. **Per-Request Credentials**: Claude will prompt for credentials when needed

For detailed credential patterns, see [MCP_CREDENTIAL_PATTERNS.md](MCP_CREDENTIAL_PATTERNS.md)

## Troubleshooting

### Enable Debug Logging

Add verbose flag to see detailed logs:

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "args": ["-v"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Test Outside Claude Desktop

Test the server directly:

```bash
# Test initialization
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05"}}' | awswhitelist

# Test tools list
echo '{"jsonrpc":"2.0","method":"tools/list","id":2,"params":{}}' | awswhitelist
```

### Common Issues

1. **"Method not found: tools/call"**: Update to version 1.1.10 or later
2. **Import errors**: Ensure all dependencies are installed with `pip install awswhitelist-mcp`
3. **Permission errors**: Check AWS IAM permissions
4. **Connection errors**: Verify network connectivity to AWS
5. **Invalid JSON**: Enable verbose logging to debug
6. **"Unexpected end of JSON input"**: Update to version 1.1.6 or later

## Environment Variables

You can set these environment variables:

- `AWS_WHITELIST_CONFIG`: Path to configuration file
- `AWS_WHITELIST_LOG_LEVEL`: Set to DEBUG for verbose output
- `AWS_DEFAULT_REGION`: Default AWS region

Example:

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "AWS_WHITELIST_LOG_LEVEL": "DEBUG",
        "AWS_DEFAULT_REGION": "us-west-2"
      }
    }
  }
}
```