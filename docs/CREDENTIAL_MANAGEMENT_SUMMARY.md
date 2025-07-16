# Credential Management Summary

## Quick Overview

The AWS Whitelist MCP Server now supports multiple ways to manage AWS credentials, making it much easier and more secure to use:

## 1. Named Profiles (Recommended)

Instead of passing credentials in every request, define profiles in `mcp_config.json`:

```json
{
  "credentials": {
    "profiles": {
      "production": {
        "source": "environment",
        "region": "us-east-1"
      },
      "development": {
        "source": "file",
        "credential_file": "~/.aws/credentials",
        "profile_name": "dev"
      }
    }
  }
}
```

Then use them simply:
```json
{
  "method": "aws.whitelist",
  "params": {
    "profile": "production",
    "resource_id": "sg-123456",
    "ip_address": "current"
  }
}
```

## 2. Credential Sources

The server supports multiple credential sources:
- **Environment Variables**: Uses AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
- **IAM Roles**: For EC2/ECS/Lambda environments
- **AWS CLI Config**: Uses ~/.aws/credentials
- **Secrets Manager**: Fetches from AWS Secrets Manager
- **Explicit**: Still supported but not recommended

## 3. Smart Defaults

Configure common parameters once:
```json
{
  "defaults": {
    "region": "us-east-1",
    "port": 443,
    "protocol": "tcp"
  }
}
```

## 4. Named Constants

Use friendly names instead of numbers:
- Ports: `"https"` → 443, `"ssh"` → 22
- Port ranges: `"ephemeral"` → 49152-65535
- Special values: `"current"` → auto-detect your IP

## 5. Benefits

- **Security**: No credentials in request logs
- **Convenience**: Shorter, simpler requests
- **Flexibility**: Multiple credential sources
- **Safety**: Credentials never stored by MCP server
- **Compatibility**: Works with existing AWS tools

## Example: Before vs After

### Before (Complex)
```json
{
  "method": "aws.whitelist",
  "params": {
    "credentials": {
      "access_key_id": "AKIAIOSFODNN7EXAMPLE",
      "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    },
    "region": "us-east-1",
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "192.168.1.100/32",
    "port": 443,
    "protocol": "tcp"
  }
}
```

### After (Simple)
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "current",
    "port": "https"
  }
}
```

## Setup Steps

1. Configure profiles in `mcp_config.json`
2. Set up credential source (env vars, IAM role, etc.)
3. Use profile names in requests
4. Enjoy simpler, more secure operations!