# AWS Whitelist MCP Server Requirements

## Project Overview
Build a Model Context Protocol (MCP) server that enables AI assistants to manage AWS resource IP whitelisting through a standardized interface. The server will accept AWS credentials, resource identifiers, and IP addresses/ranges to whitelist, execute the whitelisting operation, and return results in an MCP-compliant format.

## Functional Requirements

### 1. MCP Server Implementation
- Implement a fully compliant MCP server following the Model Context Protocol specification
- Support standard MCP server discovery and initialization
- Provide proper MCP response formatting for all operations
- Handle MCP protocol errors gracefully

### 2. Core Functionality
- **Input Parameters:**
  - Profile name OR explicit AWS credentials
  - AWS region (with defaults)
  - Resource type (with shortcuts)
  - Resource identifier or name
  - IP address, CIDR block, or "current" for auto-detection
  - Optional rule description (with template support)
  - Optional port/protocol specification (with named ports)

- **Credential Management:**
  - Named credential profiles
  - Environment variable support
  - AWS CLI credentials file integration
  - IAM role assumption
  - AWS Secrets Manager integration
  - Credential provider chain
  - No credential storage in MCP server

- **Parameter Defaults and Constants:**
  - Configurable default values
  - Named port mappings (https→443, ssh→22, etc.)
  - Port range shortcuts (ephemeral, highports, etc.)
  - Auto IP detection option
  - Template-based descriptions

- **Supported AWS Resources:**
  - EC2 Security Groups
  - RDS DB Instances (via security groups)
  - ElastiCache Clusters (via security groups)
  - Application Load Balancers (via security groups)
  - Network Load Balancers (via security groups)
  - Resource lookup by name/tag

### 3. Operations
- Add IP/CIDR to security group ingress rules
- Validate IP addresses and CIDR notation
- Check for existing rules to prevent duplicates
- Support both IPv4 and IPv6 addresses

### 4. Security Requirements
- Never store AWS credentials
- Credentials must be provided per request
- Support temporary credentials with session tokens
- Validate all inputs before AWS API calls
- Use AWS SDK best practices for credential handling

### 5. Error Handling
- Comprehensive error handling for:
  - Invalid AWS credentials
  - Insufficient permissions
  - Invalid resource identifiers
  - Malformed IP addresses/CIDR blocks
  - AWS API rate limiting
  - Network connectivity issues
  - boto3 client exceptions
- Return structured error messages in MCP format
- Log all errors with appropriate detail levels

### 6. Logging
- Implement structured logging using Python logging module
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Log entries must include:
  - Timestamp
  - Operation type
  - Resource type and identifier
  - IP/CIDR being whitelisted
  - Success/failure status
  - Error details (if applicable)
  - Execution duration
- Never log sensitive information (credentials)
- Support JSON formatted logs for structured logging

### 7. Response Format
- MCP-compliant JSON responses
- Include operation status (success/failure)
- Provide descriptive messages
- Return relevant metadata (rule ID, timestamp, etc.)

## Technical Requirements

### 1. Technology Stack
- Language: Python 3.10+
- AWS SDK: boto3
- MCP Implementation: Custom implementation following protocol specification
- Logging: Python logging with JSON formatter
- Configuration: JSON/YAML configuration files
- IP Validation: ipaddress module (built-in)
- Type Hints: Full typing support with mypy compatibility

### 2. Architecture
- Stateless service (no backend storage required)
- Object-oriented design with:
  - MCP protocol handling classes
  - AWS service wrapper classes
  - Validator classes
  - Response formatter classes
- Abstract base classes for extensibility
- Dependency injection pattern for testability

### 3. Performance
- Asynchronous operations where beneficial (asyncio support)
- Connection pooling for AWS clients
- Timeout handling for AWS operations (30 seconds default)
- Efficient memory usage (no credential caching)

### 4. Development Requirements
- Unit tests using pytest
- Integration tests with moto (AWS mocking)
- Code coverage > 80%
- Type checking with mypy
- Code formatting with black
- Linting with flake8/ruff
- Documentation with docstrings

## Non-Functional Requirements

### 1. Reliability
- Graceful degradation on AWS service issues
- Retry logic with exponential backoff
- Circuit breaker pattern for AWS API calls
- Proper exception handling and recovery

### 2. Maintainability
- Clean code principles
- SOLID design principles
- Comprehensive docstrings
- Modular architecture for easy extension
- Configuration management best practices

### 3. Usability
- Clear, actionable error messages
- Intuitive parameter naming
- Comprehensive examples in documentation
- Easy installation via pip

### 4. Deployment
- Support for virtual environments
- Docker container support
- Requirements.txt for dependencies
- Easy systemd service integration
- Cross-platform compatibility (Windows/Linux/macOS)

## Out of Scope
- Persistent storage of any kind
- Web UI or API endpoints (MCP protocol only)
- Credential management/storage
- IP blacklisting functionality
- Scheduled or batch operations
- Multi-account management
- Audit trail beyond session logging

## Success Criteria
- Successfully whitelist IPs in AWS Security Groups via MCP protocol
- Handle all error scenarios gracefully
- Return properly formatted MCP responses
- Complete operations within reasonable time limits (< 30 seconds)
- Pass all unit and integration tests
- Zero credential exposure in logs or responses
- Easy installation and deployment