# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-Cloud Whitelisting MCP Server is a Model Context Protocol (MCP) server that manages security group/firewall IP whitelisting across AWS, Azure, and Google Cloud Platform. It's a stateless service that accepts cloud credentials per request and provides secure, unified whitelisting functionality with cloud-specific optimizations.

## Key Architecture Components

### 1. MCP Protocol Layer (`awswhitelist/mcp/`)
- `handler.py`: Implements MCP request/response handling with JSON-RPC 2.0 format
- Methods: `tools/call` (standard MCP method), `tools/list`, `initialize`
- Tool names: `whitelist_add`, `whitelist_remove`, `whitelist_list`, `whitelist_check`
- Stateless design - credentials passed with each request

### 2. Cloud Service Layers
- **AWS** (`awswhitelist/aws/service.py`): EC2 Security Groups via boto3
- **Azure** (`awswhitelist/azure/service.py`): Network Security Groups via azure-mgmt-network
- **GCP** (`awswhitelist/gcp/service.py`): VPC Firewall Rules via google-cloud-compute
- Each service handles rule creation, deletion, and listing with cloud-specific logic
- GCP includes additive-only mode for safety (never modifies existing rules)

### 3. Utilities (`awswhitelist/utils/`)
- `credential_validator.py`: AWS credential validation using STS
- `ip_validator.py`: IP address/CIDR validation and normalization
- `logging.py`: Structured JSON logging configuration

### 4. Configuration (`awswhitelist/config.py`)
- Hierarchical configuration: file → environment variables → defaults
- Multi-cloud credential profiles with cloud-specific settings
- Supports port mappings, security settings, and cloud provider selection
- Uses Pydantic for validation with CloudProvider enum

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
  "method": "tools/call",
  "params": {
    "name": "whitelist_add",
    "arguments": {
      "cloud": "aws",  // aws, azure, or gcp
      "credentials": {
        "access_key_id": "AKIA...",
        "secret_access_key": "...",
        "region": "us-east-1"
      },
      "security_group_id": "sg-123456",  // or nsg_name for Azure
      "ip_address": "192.168.1.1",
      "port": 443,
      "protocol": "tcp",
      "description": "API access",
      "service_name": "https"  // optional
    }
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

- **Cloud Provider**: Select aws, azure, gcp, or all for parallel operations
- **Credential Profiles**: Named credential configurations for each cloud
- **Port Mappings**: Named ports (e.g., "https" → 443)
- **Security Settings**: MFA requirements, IP restrictions, rate limits
- **Cloud-Specific Defaults**: 
  - AWS: region, security group ID
  - Azure: resource group, NSG name
  - GCP: project ID, network, additive-only mode

## Docker Deployment

- Multi-stage build for minimal runtime image
- Runs as non-root user (mcpuser)
- Read-only filesystem with tmpfs for /tmp
- Resource limits configured
- Supports both production and development modes