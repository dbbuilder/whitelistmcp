# MCP Server Credential Management Patterns

This guide presents secure, lightweight patterns for managing credentials in MCP servers without requiring input for every request.

## Core Principle: Stateless Protocol, Stateful Environment

MCP servers must remain stateless per the protocol specification, but the execution environment can maintain credential state securely.

## 1. Environment Variable Patterns

### 1.1 Direct Environment Variables

**Implementation:**
```bash
# Set credentials before starting MCP server
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-east-1"

# Start MCP server (credentials available in process)
claude-desktop  # MCP server inherits environment
```

**Server Code Pattern:**
```python
import os
from typing import Optional, Dict, Any

class CredentialResolver:
    """Resolve credentials from multiple sources."""
    
    def get_credentials(self, request_creds: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get credentials with fallback hierarchy."""
        # 1. Use request credentials if provided
        if request_creds and self._validate_creds(request_creds):
            return request_creds
        
        # 2. Fall back to environment variables
        env_creds = {
            "access_key_id": os.environ.get("AWS_ACCESS_KEY_ID"),
            "secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY"),
            "region": os.environ.get("AWS_REGION", "us-east-1"),
            "session_token": os.environ.get("AWS_SESSION_TOKEN")
        }
        
        if self._validate_creds(env_creds):
            return env_creds
        
        # 3. No valid credentials found
        raise ValueError("No valid credentials found in request or environment")
```

### 1.2 Credential File Pattern

**Setup:**
```bash
# ~/.mcp/credentials
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...

[production]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

**Implementation:**
```python
import configparser
from pathlib import Path

class FileCredentialProvider:
    def __init__(self, profile: str = "default"):
        self.profile = os.environ.get("MCP_CREDENTIAL_PROFILE", profile)
        self.cred_file = Path.home() / ".mcp" / "credentials"
    
    def load_credentials(self):
        """Load credentials from file."""
        if not self.cred_file.exists():
            return None
        
        # Ensure file permissions are secure
        if self.cred_file.stat().st_mode & 0o077:
            raise PermissionError(f"Credentials file {self.cred_file} has insecure permissions")
        
        config = configparser.ConfigParser()
        config.read(self.cred_file)
        
        if self.profile in config:
            return dict(config[self.profile])
        return None
```

## 2. Native Platform Integration

### 2.1 Operating System Keychain

**macOS Keychain:**
```python
import subprocess
import json

class MacOSKeychainProvider:
    def get_credential(self, service: str, account: str) -> Optional[str]:
        """Retrieve credential from macOS Keychain."""
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def store_credential(self, service: str, account: str, password: str):
        """Store credential in macOS Keychain."""
        subprocess.run(
            ["security", "add-generic-password", "-s", service, "-a", account, "-w", password],
            check=True
        )
```

**Windows Credential Manager:**
```python
# Using keyring library for cross-platform support
import keyring

class WindowsCredentialProvider:
    def get_credential(self, service: str, username: str) -> Optional[str]:
        """Retrieve credential from Windows Credential Manager."""
        return keyring.get_password(service, username)
    
    def store_credential(self, service: str, username: str, password: str):
        """Store credential in Windows Credential Manager."""
        keyring.set_password(service, username, password)
```

**Linux Secret Service:**
```python
import secretstorage

class LinuxSecretProvider:
    def __init__(self):
        self.connection = secretstorage.dbus_init()
        self.collection = secretstorage.get_default_collection(self.connection)
    
    def get_credential(self, label: str) -> Optional[str]:
        """Retrieve credential from Linux Secret Service."""
        items = self.collection.search_items({"label": label})
        if items:
            return items[0].get_secret().decode('utf-8')
        return None
```

## 3. Secure Credential Patterns for MCP

### 3.1 Hybrid Approach with Override Capability

```python
class MCPCredentialManager:
    """Unified credential management for MCP servers."""
    
    def __init__(self):
        self.providers = [
            EnvironmentProvider(),
            KeychainProvider(),
            FileProvider(),
        ]
    
    def get_credentials(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get credentials with override capability."""
        # 1. Check if request includes credentials
        if "credentials" in request_params:
            creds = request_params["credentials"]
            if self._has_required_fields(creds):
                return creds
        
        # 2. Check for credential reference
        if "credential_id" in request_params:
            return self._resolve_credential_id(request_params["credential_id"])
        
        # 3. Fall back to environment providers
        for provider in self.providers:
            creds = provider.get_credentials()
            if creds and self._has_required_fields(creds):
                return creds
        
        raise ValueError("No valid credentials available")
```

### 3.2 Named Credential Profiles

```python
class ProfileBasedCredentials:
    """Support multiple named credential sets."""
    
    def __init__(self):
        self.profiles = self._load_profiles()
    
    def _load_profiles(self) -> Dict[str, Dict]:
        """Load from environment-specified config."""
        config_path = os.environ.get("MCP_PROFILES_PATH", "~/.mcp/profiles.json")
        # Implementation...
    
    def get_profile_credentials(self, profile_name: str = None) -> Dict[str, Any]:
        """Get credentials for a specific profile."""
        profile = profile_name or os.environ.get("MCP_ACTIVE_PROFILE", "default")
        
        if profile in self.profiles:
            return self.profiles[profile]
        
        raise ValueError(f"Profile '{profile}' not found")
```

## 4. Implementation Examples

### 4.1 AWS MCP Server with Smart Credentials

```python
class AWSWhitelistHandler:
    def __init__(self):
        self.cred_manager = MCPCredentialManager()
    
    def handle_whitelist_add(self, request):
        """Handle whitelist add with smart credential resolution."""
        params = request.params
        
        # Get credentials (from request or environment)
        try:
            credentials = self.cred_manager.get_credentials(params)
        except ValueError as e:
            return self.error_response(request.id, -32602, str(e))
        
        # Use credentials for AWS operation
        aws_service = AWSService(credentials)
        # ... rest of implementation
```

### 4.2 Tool Schema Supporting Multiple Credential Patterns

```json
{
  "name": "whitelist_add",
  "description": "Add IP to security group",
  "inputSchema": {
    "type": "object",
    "properties": {
      "credentials": {
        "type": "object",
        "description": "Optional: Override environment credentials",
        "properties": {
          "access_key_id": {"type": "string"},
          "secret_access_key": {"type": "string"},
          "region": {"type": "string"}
        }
      },
      "credential_profile": {
        "type": "string",
        "description": "Optional: Use named credential profile"
      },
      "security_group_id": {"type": "string"},
      "ip_address": {"type": "string"}
    },
    "required": ["security_group_id", "ip_address"]
  }
}
```

## 5. Security Best Practices

### 5.1 Credential Isolation

```python
class SecureCredentialProvider:
    """Isolate credential access with security checks."""
    
    def __init__(self):
        self._verify_environment_security()
    
    def _verify_environment_security(self):
        """Verify secure environment before accessing credentials."""
        # Check file permissions
        config_dir = Path.home() / ".mcp"
        if config_dir.exists():
            mode = config_dir.stat().st_mode
            if mode & 0o077:  # Others have access
                raise SecurityError("Config directory has insecure permissions")
        
        # Check environment
        if os.environ.get("MCP_INSECURE_MODE"):
            warnings.warn("Running in insecure mode")
```

### 5.2 Credential Rotation Support

```python
class RotatingCredentialProvider:
    """Support credential rotation without restart."""
    
    def __init__(self):
        self.cache_ttl = 300  # 5 minutes
        self._cache = {}
        self._cache_time = {}
    
    def get_credentials(self, key: str) -> Dict[str, Any]:
        """Get credentials with cache and rotation support."""
        now = time.time()
        
        # Check cache validity
        if key in self._cache:
            if now - self._cache_time[key] < self.cache_ttl:
                return self._cache[key]
        
        # Reload credentials
        creds = self._load_fresh_credentials(key)
        self._cache[key] = creds
        self._cache_time[key] = now
        
        return creds
```

## 6. Configuration Examples

### 6.1 Claude Desktop Configuration

```json
{
  "mcpServers": {
    "aws-whitelist": {
      "command": "npx",
      "args": ["awswhitelist-mcp"],
      "env": {
        "AWS_PROFILE": "production",
        "AWS_REGION": "us-east-1",
        "MCP_CREDENTIAL_PROFILE": "mcp-prod"
      }
    }
  }
}
```

### 6.2 Docker Compose with Secrets

```yaml
version: '3.8'

services:
  mcp-server:
    image: mcp/aws-whitelist
    environment:
      - AWS_PROFILE=production
      - MCP_CREDENTIAL_SOURCE=docker-secrets
    secrets:
      - aws_credentials
    
secrets:
  aws_credentials:
    file: ./secrets/aws_credentials.json
```

## 7. Testing Credential Patterns

### 7.1 Mock Credential Provider for Tests

```python
class MockCredentialProvider:
    """Test-friendly credential provider."""
    
    def __init__(self, test_creds: Dict[str, Any] = None):
        self.test_creds = test_creds or {
            "access_key_id": "test_key",
            "secret_access_key": "test_secret",
            "region": "us-east-1"
        }
    
    def get_credentials(self, *args, **kwargs):
        return self.test_creds
```

### 7.2 Environment Variable Testing

```bash
#!/bin/bash
# Test credential resolution

# Test 1: Environment credentials
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | mcp-server

# Test 2: Request override
unset AWS_ACCESS_KEY_ID
echo '{"jsonrpc":"2.0","id":1,"method":"whitelist_add","params":{"credentials":{"access_key_id":"override"}}}' | mcp-server

# Test 3: Profile-based
export MCP_CREDENTIAL_PROFILE="production"
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | mcp-server
```

## 8. Platform-Specific Patterns

### 8.1 AWS Systems Manager Parameter Store

```python
import boto3

class SSMCredentialProvider:
    """Use AWS SSM for credential storage."""
    
    def __init__(self):
        self.ssm = boto3.client('ssm')
    
    def get_credential(self, parameter_name: str) -> str:
        """Retrieve from SSM."""
        response = self.ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
```

### 8.2 HashiCorp Vault Integration

```python
import hvac

class VaultCredentialProvider:
    """Use HashiCorp Vault for secrets."""
    
    def __init__(self):
        self.client = hvac.Client(
            url=os.environ.get('VAULT_ADDR'),
            token=os.environ.get('VAULT_TOKEN')
        )
    
    def get_credentials(self, path: str) -> Dict[str, Any]:
        """Retrieve from Vault."""
        response = self.client.read(path)
        return response['data']['data']
```

## Summary

The key to secure, lightweight credential management in MCP servers is:

1. **Never store credentials in the MCP server state**
2. **Use environment-based credential providers**
3. **Support request-level credential override**
4. **Integrate with platform-native credential stores**
5. **Implement proper security checks and isolation**
6. **Provide clear documentation for setup**

This approach maintains MCP's stateless protocol while providing convenient, secure credential management.