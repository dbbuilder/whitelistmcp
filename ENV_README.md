# Environment Variables Configuration

## Overview
This project uses environment variables to securely manage AWS credentials and configuration settings. All sensitive information is stored in a `.env` file which is excluded from version control.

## Quick Setup

1. **Run the setup script** (Windows):
   ```cmd
   setup_env.bat
   ```

2. **Or manually copy the example file**:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your values**:
   ```bash
   notepad .env
   ```

## Environment Variables Reference

### AWS Credentials (Required)
- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key
- `AWS_DEFAULT_REGION` - AWS region (default: us-east-1)

### Security Group Defaults (Optional)
- `DEFAULT_SECURITY_GROUP_ID` - Default security group for operations
- `DEFAULT_SECURITY_GROUP_NAME` - Friendly name for the default SG
- `DEFAULT_VPC_ID` - Default VPC ID

### Description Format
- `DESCRIPTION_PREFIX` - Prefix for auto-generated descriptions (default: "auto")
- `DESCRIPTION_SEPARATOR` - Separator character (default: "-")
- `DESCRIPTION_TIMESTAMP_FORMAT` - Python strftime format (default: "%Y%m%d-%H%M")

### Example Description
With defaults, a rule description would look like:
```
WebApp - 8080-auto-john_doe-20250711-1430
```

### Validation Settings
- `VALIDATE_IP_FORMAT` - Enable IP validation (true/false)
- `VALIDATE_PORT_RANGE` - Enable port range validation (true/false)
- `MIN_PORT` - Minimum allowed port (default: 1)
- `MAX_PORT` - Maximum allowed port (default: 65535)

### Audit & Logging
- `ENABLE_AUDIT_LOG` - Enable audit logging (true/false)
- `AUDIT_LOG_PATH` - Path to audit log file
- `MCP_LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

### Common Ports
Pre-defined port mappings:
- `COMMON_PORTS_SSH` - SSH port (default: 22)
- `COMMON_PORTS_HTTP` - HTTP port (default: 80)
- `COMMON_PORTS_HTTPS` - HTTPS port (default: 443)
- `COMMON_PORTS_RDP` - RDP port (default: 3389)

## Using Environment Variables in Scripts

### Python Scripts
All scripts automatically load from `.env` if the `config_manager` module is available:

```python
# Script will use environment variables automatically
python simple_test/add_sg_rule_env.py '{"UserName":"test","UserIP":"1.1.1.1","Port":"8080","SecurityGroupID":"sg-123","ResourceName":"App"}'
```

### MCP Server
The MCP server (`server_env.py`) automatically uses environment variables:

```python
python mcp_server/server_env.py
```

### Override Environment File
You can specify a different environment file:

```bash
python simple_test/add_sg_rule_env.py --env-file .env.production '{"UserName":"test",...}'
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use different `.env` files** for different environments:
   - `.env.development`
   - `.env.staging`
   - `.env.production`

3. **Minimal permissions** - Use AWS IAM policies with least privilege
4. **Rotate credentials** regularly
5. **Use AWS IAM roles** when running on EC2 or Lambda

## JSON Structure Template

The `JSON_TEMPLATE` environment variable documents the expected JSON structure:

```json
{
  "UserName": "string",
  "UserIP": "string",
  "Port": "string",
  "SecurityGroupID": "string",
  "ResourceName": "string"
}
```

## Testing Configuration

Test your environment setup:

```python
# Test configuration loading
python config_manager.py

# Test AWS connection with environment variables
python simple_test/test_aws_access.py
```

## Troubleshooting

### Module Not Found
If you get "config_manager not found", install dependencies:
```bash
pip install python-dotenv boto3
```

### AWS Credentials Not Found
1. Check `.env` file exists
2. Verify credentials are set correctly
3. Ensure no extra spaces or quotes

### Permission Denied
Ensure AWS credentials have these permissions:
- `ec2:DescribeSecurityGroups`
- `ec2:AuthorizeSecurityGroupIngress`
- `ec2:RevokeSecurityGroupIngress`

## Advanced Usage

### Multiple Environments
```bash
# Development
ENV_FILE=.env.dev python simple_test/add_sg_rule_env.py ...

# Production
ENV_FILE=.env.prod python simple_test/add_sg_rule_env.py ...
```

### Export Configuration
View current configuration:
```python
from config_manager import get_config
config = get_config()
config.export_config('current_config.json')
```

### Custom Validation
Add custom validation in `config_manager.py`:
```python
def validate_custom_rule(ip, port):
    config = get_config()
    # Your validation logic
    return True
```