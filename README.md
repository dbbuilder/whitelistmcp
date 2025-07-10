# AWS Whitelist MCP Server

A Model Context Protocol (MCP) server that enables AI assistants to manage AWS resource IP whitelisting through a standardized interface.

## Overview

This MCP server provides a secure, stateless service for adding IP addresses and CIDR blocks to AWS Security Groups. It supports various AWS resources including EC2, RDS, ElastiCache, and Load Balancers, all through their associated security groups.

## Features

- **MCP Compliant**: Fully implements the Model Context Protocol specification
- **Multi-Resource Support**: Works with EC2, RDS, ElastiCache, ALB, and NLB
- **Secure**: Stateless design with no credential storage
- **Comprehensive Logging**: Structured JSON logging
- **Error Handling**: Robust error handling with retry logic
- **IP Validation**: Supports both IPv4 and IPv6 with CIDR notation
- **Type Safety**: Full type hints for better IDE support and validation

## Prerequisites

- Python 3.10 or higher
- AWS Account with appropriate permissions
- Git for version control
- pip for package management

## Installation

1. Clone the repository:
```bash
git clone https://github.com/[your-username]/awswhitelist2.git
cd awswhitelist2
```

2. Create a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/macOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install development dependencies (optional):
```bash
pip install -r requirements-dev.txt
```

5. Run tests:
```bash
pytest
```

## Configuration

Configure the application using `mcp_config.json`. See [CREDENTIAL_MANAGEMENT_DESIGN.md](docs/CREDENTIAL_MANAGEMENT_DESIGN.md) for detailed configuration options.

### Basic Configuration
```json
{
  "credentials": {
    "default_profile": "default",
    "profiles": {
      "default": {
        "source": "environment",
        "region": "us-east-1"
      }
    }
  },
  "defaults": {
    "region": "us-east-1",
    "port": 443,
    "protocol": "tcp"
  }
}
```

## Usage

### Starting the MCP Server

```bash
python -m awswhitelist.server
```

### MCP Request Format

The MCP server supports multiple credential management options:

#### Option 1: Using Named Profiles (Recommended)
```json
{
  "method": "aws.whitelist",
  "params": {
    "profile": "production",
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "192.168.1.100/32"
  }
}
```

#### Option 2: Minimal Request (Using Defaults)
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0"
  }
}
```

#### Option 3: Explicit Credentials (Not Recommended)
```json
{
  "method": "aws.whitelist",
  "params": {
    "credentials": {
      "access_key_id": "AKIAIOSFODNN7EXAMPLE",
      "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
      "session_token": "optional-session-token"
    },
    "region": "us-east-1",
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "192.168.1.100/32",
    "port": 443
  }
}
```

### Special Features

- **Auto-detect IP**: Use `"ip_address": "current"` to automatically detect your public IP
- **Named ports**: Use `"port": "https"` instead of `443`
- **Resource lookup**: Use `"resource_name": "web-server-sg"` to find by tag name
- **Bulk operations**: Use `aws.whitelist_bulk` method to add multiple rules at once

See [MCP_REQUEST_EXAMPLES.md](docs/MCP_REQUEST_EXAMPLES.md) for more examples.

### Response Format

Success response:
```json
{
  "success": true,
  "message": "Successfully added IP 192.168.1.100/32 to security group sg-0123456789abcdef0",
  "data": {
    "rule_id": "sgr-0123456789abcdef0",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

Error response:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "The provided AWS credentials are invalid or expired"
  }
}
```

## Security Considerations

- **Credentials**: Never stored; must be provided with each request
- **Logging**: Sensitive information is automatically redacted
- **Validation**: All inputs are validated before AWS API calls
- **Permissions**: Requires appropriate AWS IAM permissions for security group modifications

## Required AWS Permissions

The IAM user/role must have the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:DescribeSecurityGroupRules"
      ],
      "Resource": "*"
    }
  ]
}
```

## Project Structure

```
awswhitelist2/
├── awswhitelist/
│   ├── __init__.py
│   ├── server.py
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── protocol.py
│   │   ├── handlers.py
│   │   └── models.py
│   ├── aws/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── security_groups.py
│   │   └── validators.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   └── validators.py
│   └── config.py
├── tests/
│   ├── __init__.py
│   ├── test_mcp/
│   ├── test_aws/
│   └── test_utils/
├── scripts/
│   └── setup.sh
├── docker/
│   └── Dockerfile
├── logs/
├── config.json
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── pytest.ini
├── .gitignore
├── README.md
├── REQUIREMENTS.md
├── TODO.md
└── FUTURE.md
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/[your-username]/awswhitelist2.git
cd awswhitelist2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=awswhitelist --cov-report=html

# Run specific test file
pytest tests/test_aws/test_security_groups.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Type checking
mypy awswhitelist

# Code formatting
black awswhitelist tests

# Linting
flake8 awswhitelist tests

# Or use pre-commit for all checks
pre-commit run --all-files
```

## Docker Support

Build and run with Docker:

```bash
# Build image
docker build -t awswhitelist-mcp .

# Run container
docker run -it awswhitelist-mcp

# With custom config
docker run -it -v $(pwd)/config.json:/app/config.json awswhitelist-mcp
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**: 
   - Verify AWS credentials are valid
   - Check IAM permissions
   - Ensure session token is included if using temporary credentials

2. **Network Timeouts**: 
   - Check network connectivity
   - Verify AWS service endpoints are accessible
   - Increase timeout in configuration

3. **Invalid IP Format**: 
   - Use proper CIDR notation (e.g., 192.168.1.1/32)
   - For single IPs, always include /32 suffix
   - Ensure IPv6 addresses are properly formatted

### Debug Mode

Enable debug logging by modifying `config.json`:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

Or set environment variable:
```bash
export AWS_WHITELIST_LOG_LEVEL=DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for all public functions
- Maintain test coverage above 80%
- Update documentation as needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check existing issues for solutions
- Review the logs for detailed error information

## Acknowledgments

- boto3 - AWS SDK for Python
- Model Context Protocol specification
- Python logging cookbook
- AWS documentation