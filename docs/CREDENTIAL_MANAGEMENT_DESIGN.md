# MCP Server Configuration and Credential Management Design

## Overview

This document outlines how to implement credential management and parameter standardization in the AWS Whitelist MCP Server to improve usability and security.

## 1. Credential Management Options

### Option A: Named Credential Profiles
Store credentials in a secure local file with named profiles, similar to AWS CLI:

```json
{
  "method": "aws.whitelist",
  "params": {
    "profile": "production",  // Reference a named profile
    "region": "us-east-1",
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "192.168.1.100/32"
  }
}
```

### Option B: Environment-Based Credentials
Use environment variables with MCP server configuration:

```json
{
  "method": "aws.whitelist",
  "params": {
    "use_environment_credentials": true,  // Use AWS_ACCESS_KEY_ID, etc.
    "region": "us-east-1",
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "192.168.1.100/32"
  }
}
```

### Option C: MCP Server Configuration
Configure default credentials in the MCP server setup:

```json
// mcp_config.json
{
  "aws": {
    "default_profile": "production",
    "profiles": {
      "production": {
        "credential_source": "environment",  // or "iam_role", "file"
        "region": "us-east-1"
      },
      "development": {
        "credential_source": "file",
        "credential_file": "~/.aws/credentials",
        "profile_name": "dev",
        "region": "us-west-2"
      }
    }
  }
}
```

### Option D: Credential Provider Chain
Implement AWS SDK-style credential provider chain:

1. Explicit credentials in request (highest priority)
2. Named profile in request
3. Environment variables
4. IAM role (if running on EC2/ECS/Lambda)
5. Default profile from config

## 2. Parameter Standardization

### Default Values Configuration
```json
// mcp_config.json
{
  "defaults": {
    "region": "us-east-1",
    "port": 443,
    "protocol": "tcp",
    "description_template": "{user} - {date} - {source_ip}",
    "ip_address": "current"  // Special value to detect caller's IP
  },
  "constants": {
    "common_ports": {
      "https": 443,
      "http": 80,
      "ssh": 22,
      "rdp": 3389,
      "mysql": 3306,
      "postgres": 5432
    },
    "resource_types": {
      "ec2": "SecurityGroup",
      "rds": "RDSSecurityGroup",
      "elb": "LoadBalancer"
    }
  }
}
```

### Simplified Request Format
With defaults and constants, requests become simpler:

```json
{
  "method": "aws.whitelist",
  "params": {
    "profile": "production",
    "resource_id": "sg-0123456789abcdef0",
    "port": "https"  // Resolves to 443
  }
}
```

## 3. Resource Discovery Features

### A. List Available Resources
```json
{
  "method": "aws.list_security_groups",
  "params": {
    "profile": "production",
    "filters": {
      "tag:Environment": "Production"
    }
  }
}
```

### B. Resource Lookup by Name
```json
{
  "method": "aws.whitelist",
  "params": {
    "profile": "production",
    "resource_name": "web-server-sg",  // Lookup by name tag
    "port": "https"
  }
}
```

## 4. Implementation Architecture

### Credential Manager Class
```python
class CredentialManager:
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.providers = self._initialize_providers()
    
    def get_credentials(self, request_params: dict) -> AwsCredentials:
        # Implement credential provider chain
        for provider in self.providers:
            creds = provider.get_credentials(request_params)
            if creds:
                return creds
        raise NoCredentialsError()
```

### Parameter Resolver Class
```python
class ParameterResolver:
    def __init__(self, config: dict):
        self.defaults = config.get('defaults', {})
        self.constants = config.get('constants', {})
    
    def resolve_params(self, params: dict) -> dict:
        resolved = self.defaults.copy()
        resolved.update(params)
        
        # Resolve constants
        if 'port' in resolved and isinstance(resolved['port'], str):
            resolved['port'] = self.constants['common_ports'].get(
                resolved['port'], resolved['port']
            )
        
        # Auto-detect IP if requested
        if resolved.get('ip_address') == 'current':
            resolved['ip_address'] = self._detect_current_ip()
        
        return resolved
```

## 5. Security Considerations

### Credential Storage
- Never store credentials in plain text
- Use OS keyring/keychain where available
- Encrypt credential files at rest
- Support AWS Secrets Manager integration
- Implement credential rotation reminders

### Access Control
- Implement MCP-level authentication
- Log all credential usage
- Support read-only credential profiles
- Implement rate limiting per profile

## 6. MCP Methods

### Core Methods
```python
# Whitelist with simplified params
aws.whitelist

# Credential management
aws.list_profiles
aws.test_credentials

# Resource discovery
aws.list_security_groups
aws.find_security_group
aws.list_regions

# Current IP detection
aws.get_my_ip

# Bulk operations
aws.whitelist_bulk
```

## 7. Configuration File Structure

### Complete MCP Configuration
```json
{
  "server": {
    "name": "aws-whitelist",
    "version": "1.0.0"
  },
  "credentials": {
    "default_profile": "production",
    "provider_chain": [
      "explicit",
      "profile",
      "environment",
      "iam_role",
      "config_file"
    ],
    "profiles": {
      "production": {
        "source": "iam_role",
        "role_arn": "arn:aws:iam::123456789012:role/WhitelistRole",
        "region": "us-east-1"
      },
      "development": {
        "source": "environment",
        "region": "us-west-2"
      }
    }
  },
  "defaults": {
    "region": "us-east-1",
    "port": 443,
    "protocol": "tcp",
    "description": "MCP Whitelist - {timestamp}",
    "auto_detect_ip": false
  },
  "features": {
    "resource_lookup": true,
    "bulk_operations": true,
    "ip_detection": true,
    "credential_caching": true,
    "cache_ttl_seconds": 3600
  },
  "security": {
    "require_mcp_auth": false,
    "allowed_profiles": ["production", "development"],
    "rate_limit": {
      "requests_per_minute": 60,
      "requests_per_hour": 1000
    }
  }
}
```

## 8. Usage Examples

### Minimal Request (using all defaults)
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0"
  }
}
```

### Using Named Profile
```json
{
  "method": "aws.whitelist",
  "params": {
    "profile": "development",
    "resource_name": "dev-api-sg",
    "ip_address": "current"
  }
}
```

### Bulk Operation
```json
{
  "method": "aws.whitelist_bulk",
  "params": {
    "profile": "production",
    "rules": [
      {
        "resource_id": "sg-001",
        "ip_address": "10.0.1.0/24",
        "port": "https"
      },
      {
        "resource_id": "sg-002",
        "ip_address": "10.0.2.0/24",
        "port": "ssh"
      }
    ]
  }
}
```

## 9. Benefits

1. **Improved Security**: Credentials not passed in every request
2. **Better UX**: Simpler requests with smart defaults
3. **Flexibility**: Multiple credential sources supported
4. **Discovery**: Can find resources by name/tags
5. **Automation**: Bulk operations and IP detection
6. **Compatibility**: Works with existing AWS tooling

## 10. Migration Path

### Phase 1: Basic Implementation
- Credential profiles in config file
- Basic parameter defaults
- Environment variable support

### Phase 2: Enhanced Features
- AWS Secrets Manager integration
- Resource discovery methods
- Bulk operations

### Phase 3: Advanced Features
- OS keyring integration
- IAM role assumption
- Cross-account support
- Audit logging