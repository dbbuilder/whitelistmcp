# AWS Credentials Guide for Claude Desktop

The AWS Whitelisting MCP Server is **stateless** and does **not store credentials**. AWS credentials must be provided with each request for security. Here's how to handle credentials when using the server with Claude Desktop.

## Methods for Providing Credentials

### 1. Let Claude Desktop Prompt You (Most Secure)

When you ask Claude to whitelist an IP, it will recognize that credentials are needed and ask you to provide them. For example:

**You:** "Add my current IP to security group sg-123456 for HTTPS access"

**Claude:** "I'll help you add your IP to the security group. I'll need your AWS credentials to proceed. Please provide:
- AWS Access Key ID
- AWS Secret Access Key  
- AWS Region (e.g., us-east-1)"

**You:** "Access Key: AKIAXXXXXXX, Secret Key: xxxxxxxxx, Region: us-east-1"

### 2. Include Credentials in Your Request

You can provide credentials directly in your message:

**You:** "Add IP 192.168.1.100 to security group sg-123456 on port 443. Use these credentials: Access Key ID: AKIAXXXXXXX, Secret Access Key: xxxxxxxxx, Region: us-east-1"

### 3. Use Environment Variables (Development Only)

For development/testing, you can configure the MCP server to read from environment variables:

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "args": [],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "AWS_ACCESS_KEY_ID": "AKIAXXXXXXX",
        "AWS_SECRET_ACCESS_KEY": "xxxxxxxxx",
        "AWS_DEFAULT_REGION": "us-east-1"
      }
    }
  }
}
```

**⚠️ WARNING:** This stores credentials in plain text. Only use for development!

### 4. Use AWS Credentials File (Development Only)

Configure the server to use AWS CLI credentials:

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "args": ["-c", "config_with_profile.json"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "AWS_PROFILE": "myprofile"
      }
    }
  }
}
```

Create `config_with_profile.json`:
```json
{
  "credential_profiles": [
    {
      "name": "default",
      "use_aws_profile": true,
      "aws_profile_name": "myprofile"
    }
  ]
}
```

### 5. Use Temporary Credentials (Recommended for Production)

Use AWS STS to generate temporary credentials:

```bash
# Generate temporary credentials
aws sts get-session-token --duration-seconds 3600

# Use the temporary credentials in Claude
```

**You:** "Add my IP to sg-123456. Credentials: Access Key: ASIAXXXXXXX, Secret Key: xxxxxxxxx, Session Token: xxxxxxxxx, Region: us-east-1"

## Security Best Practices

### 1. **Never Share Credentials in Screenshots**
If you're sharing screenshots of Claude conversations, always redact credentials.

### 2. **Use IAM Roles When Possible**
If running on EC2 or AWS infrastructure, use IAM roles instead of credentials.

### 3. **Minimal Permissions**
Create an IAM user with only the required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

### 4. **Rotate Credentials Regularly**
Change your AWS access keys periodically.

### 5. **Use MFA**
Enable MFA on your AWS account for additional security.

## Configuration Examples

### Basic Configuration (Prompts for Credentials)

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

### With Default Region

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "args": ["-c", "config.json"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

`config.json`:
```json
{
  "default_parameters": {
    "region": "us-east-1"
  }
}
```

### With Named Profiles (Advanced)

```json
{
  "credential_profiles": [
    {
      "name": "production",
      "description": "Production AWS account",
      "required_iam_roles": ["arn:aws:iam::123456789012:role/SecurityAdmin"]
    },
    {
      "name": "development",
      "description": "Development AWS account",
      "required_iam_roles": ["arn:aws:iam::098765432109:role/Developer"]
    }
  ]
}
```

## Credential Flow Diagram

```
User Request → Claude Desktop → MCP Server → AWS API
     ↓              ↓               ↓          ↓
"Add my IP"   "Need creds?"   Pass creds   Validate
     ↓              ↓               ↓          ↓
 Provides      Formats as      Executes    Returns
  creds        MCP request      request     result
```

## Troubleshooting Credentials

### Common Errors

1. **"Invalid credentials"**
   - Check for typos in access key or secret
   - Ensure credentials are active in AWS IAM
   - Verify correct region

2. **"Access Denied"**
   - Check IAM permissions
   - Ensure user has EC2 security group permissions
   - Verify security group exists in the specified region

3. **"Credential validation failed"**
   - Check network connectivity
   - Verify STS endpoint is accessible
   - Check for corporate proxy/firewall

### Debug Credential Issues

Enable verbose logging:

```json
{
  "mcpServers": {
    "awswhitelist": {
      "command": "awswhitelist",
      "args": ["-v"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "AWS_WHITELIST_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## Credential Prompt Templates

Claude will typically format credential requests like:

```json
{
  "method": "whitelist/add",
  "params": {
    "credentials": {
      "access_key_id": "AKIAIOSFODNN7EXAMPLE",
      "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "region": "us-east-1",
      "session_token": "optional-for-temporary-credentials"
    },
    "security_group_id": "sg-123456",
    "ip_address": "192.168.1.100",
    "port": 443,
    "protocol": "tcp",
    "description": "Added via Claude Desktop"
  }
}
```

## Important Notes

1. **Credentials are never stored** by the MCP server
2. **Each request requires credentials** - this is by design for security
3. **Claude Desktop handles the credential flow** - you just provide them when asked
4. **Consider using read-only credentials** for listing operations
5. **Use temporary credentials** when possible for better security