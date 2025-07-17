# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Whitelisting MCP Server is a Model Context Protocol (MCP) server that manages AWS Security Group IP whitelisting. It's a stateless service that accepts AWS credentials per request and provides secure IP whitelisting functionality.

## Key Architecture Components

### 1. MCP Protocol Layer (`awswhitelist/mcp/`)
- `handler.py`: Implements MCP request/response handling with JSON-RPC 2.0 format
- Methods: `tools/call` (standard MCP method), `tools/list`, `initialize`
- Tool names: `whitelist_add`, `whitelist_remove`, `whitelist_list`, `whitelist_check`
- Stateless design - credentials passed with each request

### 2. AWS Service Layer (`awswhitelist/aws/`)
- `service.py`: Wraps boto3 EC2 client for security group operations
- Handles rule creation, deletion, and listing with proper error handling
- Uses Pydantic models for type safety

### 3. Utilities (`awswhitelist/utils/`)
- `credential_validator.py`: AWS credential validation using STS
- `ip_validator.py`: IP address/CIDR validation and normalization
- `logging.py`: Structured JSON logging configuration

### 4. Configuration (`awswhitelist/config.py`)
- Hierarchical configuration: file → environment variables → defaults
- Supports credential profiles, port mappings, and security settings
- Uses Pydantic for validation

## Common Development Commands

```bash
# Development setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .

# Run tests
pytest                    # Run all tests
pytest tests/unit/       # Run unit tests only
pytest -v --cov=awswhitelist  # With coverage

# Code quality
black awswhitelist/      # Format code
flake8 awswhitelist/     # Lint code
mypy awswhitelist/       # Type checking

# Run the server
python -m awswhitelist.main              # Default mode
python -m awswhitelist.main -c config.json  # With config file
python -m awswhitelist.main -v           # Verbose logging

# Docker operations
docker-compose build                      # Build image
docker-compose up awswhitelist           # Run production
docker-compose up awswhitelist-dev       # Run development
```

## Testing Approach

- **Unit Tests**: Test individual components in isolation using mocks
- **Integration Tests**: Test end-to-end flows with mocked AWS services
- **Test Coverage**: Aim for >90% coverage
- **Fixtures**: Shared test fixtures in `tests/conftest.py`

## MCP Request/Response Format

### Add Whitelist Rule Request:
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "whitelist_add",
  "params": {
    "credentials": {
      "access_key_id": "AKIA...",
      "secret_access_key": "...",
      "region": "us-east-1"
    },
    "security_group_id": "sg-123456",
    "ip_address": "192.168.1.1",
    "port": 443,
    "protocol": "tcp",
    "description": "API access"
  }
}
```

### Success Response:
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "success": true,
    "message": "Rule added successfully",
    "rule": {
      "group_id": "sg-123456",
      "cidr_ip": "192.168.1.1/32",
      "port": 443,
      "protocol": "tcp"
    }
  }
}
```

## Security Considerations

1. **No Credential Storage**: All credentials are transient, passed per request
2. **Credential Validation**: Uses STS GetCallerIdentity to validate credentials
3. **Input Validation**: Strict validation of IPs, ports, and parameters
4. **Audit Logging**: All operations logged with request IDs
5. **Rate Limiting**: Configurable rate limits per configuration

## Error Handling

- MCP error codes follow JSON-RPC 2.0 specification
- AWS errors are wrapped with appropriate MCP error codes
- All errors include descriptive messages and optional data
- Comprehensive logging for troubleshooting

## Configuration Options

- **Credential Profiles**: Named AWS credential configurations
- **Port Mappings**: Named ports (e.g., "https" → 443)
- **Security Settings**: MFA requirements, IP restrictions, rate limits
- **Default Parameters**: Region, port, protocol, description templates

## Docker Deployment

- Multi-stage build for minimal runtime image
- Runs as non-root user (mcpuser)
- Read-only filesystem with tmpfs for /tmp
- Resource limits configured
- Supports both production and development modes