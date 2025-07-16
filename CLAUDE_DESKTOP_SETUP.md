# Claude Desktop Setup Guide

This guide explains how to install and configure the AWS Whitelisting MCP Server for use with Claude Desktop.

## Installation Options

### Option 1: Install from PyPI (Recommended)

1. Install the package:
   ```bash
   pip install awswhitelist-mcp
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

Claude will translate this to the appropriate MCP call:

```json
{
  "method": "whitelist/add",
  "params": {
    "credentials": {
      "access_key_id": "YOUR_KEY",
      "secret_access_key": "YOUR_SECRET",
      "region": "us-east-1"
    },
    "security_group_id": "sg-123456789",
    "port": 443,
    "protocol": "tcp",
    "description": "HTTPS access"
  }
}
```

## Available Methods

The server provides these MCP methods:

1. **whitelist/add** - Add an IP to a security group
2. **whitelist/remove** - Remove an IP from a security group
3. **whitelist/list** - List all rules in a security group
4. **whitelist/check** - Check if an IP is whitelisted

## Security Notes

- AWS credentials are passed with each request (stateless)
- Never store credentials in configuration files
- Claude Desktop will handle credential prompting
- Consider using AWS IAM roles or temporary credentials

For detailed information on how to provide credentials, see [CREDENTIALS_GUIDE.md](CREDENTIALS_GUIDE.md)

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
echo '{"jsonrpc":"2.0","method":"whitelist/list","id":"test","params":{"credentials":{"access_key_id":"YOUR_KEY","secret_access_key":"YOUR_SECRET","region":"us-east-1"},"security_group_id":"sg-123456"}}' | awswhitelist
```

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
2. **Permission errors**: Check AWS IAM permissions
3. **Connection errors**: Verify network connectivity to AWS
4. **Invalid JSON**: Enable verbose logging to debug

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