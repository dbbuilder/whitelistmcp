# AWS Security Group Management System

[![PyPI version](https://badge.fury.io/py/awswhitelist-mcp.svg)](https://pypi.org/project/awswhitelist-mcp/)
[![Python versions](https://img.shields.io/pypi/pyversions/awswhitelist-mcp.svg)](https://pypi.org/project/awswhitelist-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive solution for managing AWS EC2 Security Group rules with environment variable configuration, Model Context Protocol (MCP) server integration, and secure credential management.

## 🚀 Features

- **Environment-based Configuration**: Secure credential management using `.env` files
- **MCP Server Integration**: Compatible with Claude Desktop and other MCP clients
- **Flexible Rule Management**: Add, list, and manage security group rules
- **Audit Logging**: Track all changes with timestamps and user attribution
- **Description Formatting**: Standardized rule descriptions with timestamps
- **Validation**: IP address and port validation with configurable rules
- **JSON-based Interface**: Easy integration with automation tools

## 📁 Project Structure

```
D:\dev2\awswhitelist2\
├── .env                      # Environment configuration (create from .env.example)
├── .env.example              # Template for environment variables
├── .gitignore               # Git ignore rules
├── config_manager.py        # Centralized configuration management
├── test_environment.py      # Environment setup verification
├── setup_env.bat           # Windows setup script
├── ENV_README.md           # Environment variables documentation
│
├── simple_test/            # Core scripts
│   ├── test_aws_access.py  # Test AWS connectivity
│   ├── add_sg_rule_json.py # Original JSON-based script
│   ├── add_sg_rule_env.py  # Environment-aware version
│   └── ...                 # Other utility scripts
│
└── mcp_server/             # MCP server implementation
    ├── server.py           # Original Python MCP server
    ├── server_env.py       # Environment-aware MCP server
    ├── index.ts            # TypeScript MCP server
    └── claude_desktop_config_env.json  # Claude Desktop config
```

## 🔧 Quick Start

### Claude Desktop Integration

This MCP server is fully compatible with Claude Desktop. See [CLAUDE_DESKTOP_SETUP.md](CLAUDE_DESKTOP_SETUP.md) for installation instructions.

## 🔧 Quick Start

### 1. Setup Environment

**Windows:**
```cmd
setup_env.bat
```

**Manual:**
```bash
cp .env.example .env
# Edit .env with your AWS credentials
```

### 2. Install Dependencies

```bash
pip install python-dotenv boto3 mcp
```

### 3. Test Configuration

```bash
python test_environment.py
```

### 4. Test AWS Connection

```bash
python simple_test/test_aws_access.py
```

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

## 📝 Usage Examples

### Command Line Usage

**Add a security group rule:**
```bash
python simple_test/add_sg_rule_env.py '{
  "UserName": "john_doe",
  "UserIP": "203.0.113.45",
  "Port": "8080",
  "SecurityGroupID": "sg-0f0df629567eb6344",
  "ResourceName": "WebApp"
}'
```

**With dry run:**
```bash
python simple_test/add_sg_rule_env.py --dry-run '{...}'
```

**Using different environment file:**
```bash
python simple_test/add_sg_rule_env.py --env-file .env.production '{...}'
```

### MCP Server with Claude Desktop

1. **Configure Claude Desktop:**
   - Copy configuration from `mcp_server/claude_desktop_config_env.json`
   - Add to `%APPDATA%\Claude\claude_desktop_config.json`

2. **Restart Claude Desktop**

3. **Use in Claude:**
   ```
   Add IP 192.168.1.100 to security group sg-0f0df629567eb6344 on port 8080
   ```

## 🛡️ Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Use IAM roles** when running on AWS infrastructure
3. **Rotate credentials** regularly
4. **Minimal permissions** - Only grant required EC2 permissions:
   - `ec2:DescribeSecurityGroups`
   - `ec2:AuthorizeSecurityGroupIngress`
   - `ec2:RevokeSecurityGroupIngress`

## 📊 Description Format

Rules are created with standardized descriptions:
```
{ResourceName} - {Port}-auto-{UserName}-YYYYMMDD-HHMM
```

Example: `WebApp - 8080-auto-john_doe-20250711-1430`

## 🧪 Testing

**Test environment setup:**
```bash
python test_environment.py
```

**Test AWS connectivity:**
```bash
python simple_test/test_aws_access.py
```

**Test MCP server locally:**
```bash
python mcp_server/server_env.py
```

## 🔍 Troubleshooting

### Common Issues

1. **Module not found:**
   ```bash
   pip install python-dotenv boto3 mcp
   ```

2. **AWS credentials error:**
   - Check `.env` file exists and has correct values
   - Verify no extra spaces or quotes
   - Test with AWS CLI: `aws sts get-caller-identity`

3. **Permission denied:**
   - Ensure IAM user has required EC2 permissions
   - Check security group exists and is accessible

### Debug Mode

Set environment variable:
```env
MCP_LOG_LEVEL=DEBUG
```

## 📚 Advanced Usage

### Multiple Environments

```bash
# Development
ENV_FILE=.env.dev python simple_test/add_sg_rule_env.py ...

# Production  
ENV_FILE=.env.prod python simple_test/add_sg_rule_env.py ...
```

### Programmatic Usage

```python
from config_manager import get_config
import boto3

# Load configuration
config = get_config()
aws_config = config.get_aws_client_config()

# Create EC2 client
ec2 = boto3.client('ec2', **aws_config)

# Use configuration values
description = config.format_description("App", "8080", "user")
```

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

- Check [ENV_README.md](ENV_README.md) for environment configuration
- Review [TODO.md](simple_test/TODO.md) for roadmap
- See [FUTURE.md](simple_test/FUTURE.md) for enhancement ideas

---

**Note:** Remember to keep your AWS credentials secure and never commit them to version control!