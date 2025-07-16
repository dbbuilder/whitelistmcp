# MCP Request Examples

## Using the Simplified Configuration

### 1. Minimal Request (Using All Defaults)
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0"
  }
}
```
This will:
- Use default profile (environment variables)
- Use default region (us-east-1)
- Use default port (443)
- Use default protocol (tcp)
- Require manual IP address entry

### 2. Auto-Detect Current IP
```json
{
  "method": "aws.whitelist", 
  "params": {
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "current",
    "description": "My workstation"
  }
}
```

### 3. Using Named Ports
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "10.0.1.100/32",
    "port": "ssh"  // Resolves to 22
  }
}
```

### 4. Using Port Ranges
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0", 
    "ip_address": "10.0.1.0/24",
    "port_range": "ephemeral"  // Resolves to 49152-65535
  }
}
```

### 5. Using Different Profile
```json
{
  "method": "aws.whitelist",
  "params": {
    "profile": "development",
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "current"
  }
}
```

### 6. Find Security Group by Name
```json
{
  "method": "aws.find_security_group",
  "params": {
    "profile": "production",
    "name": "web-server-sg"
  }
}
```

### 7. Whitelist Using Resource Name
```json
{
  "method": "aws.whitelist",
  "params": {
    "profile": "production",
    "resource_name": "web-server-sg",  // Will lookup the ID
    "ip_address": "current",
    "port": "https"
  }
}
```

### 8. Bulk Operations
```json
{
  "method": "aws.whitelist_bulk",
  "params": {
    "profile": "production",
    "rules": [
      {
        "resource_id": "sg-001",
        "ip_address": "10.0.1.0/24", 
        "port": "https",
        "description": "Office network"
      },
      {
        "resource_id": "sg-002",
        "ip_address": "current",
        "port": "ssh",
        "description": "Admin access"
      },
      {
        "resource_name": "database-sg",
        "ip_address": "10.0.2.0/24",
        "port": "postgres"
      }
    ]
  }
}
```

### 9. List Current Rules
```json
{
  "method": "aws.list_rules",
  "params": {
    "profile": "production",
    "resource_id": "sg-0123456789abcdef0"
  }
}
```

### 10. Test Credentials
```json
{
  "method": "aws.test_credentials",
  "params": {
    "profile": "staging"
  }
}
```

## Environment Setup Examples

### Using Environment Variables
```bash
# Linux/Mac
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_DEFAULT_REGION=us-east-1

# Windows PowerShell
$env:AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
$env:AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  
$env:AWS_DEFAULT_REGION="us-east-1"
```

### Using AWS CLI Credentials File
```ini
# ~/.aws/credentials
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[dev]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

## Advanced Examples

### Custom Port Range
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "10.0.1.0/24",
    "from_port": 8080,
    "to_port": 8090,
    "protocol": "tcp"
  }
}
```

### ICMP (Ping) Access
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "10.0.1.0/24",
    "protocol": "icmp",
    "from_port": -1,
    "to_port": -1
  }
}
```

### All Traffic from Specific IP
```json
{
  "method": "aws.whitelist",
  "params": {
    "resource_id": "sg-0123456789abcdef0",
    "ip_address": "10.0.1.100/32",
    "protocol": "-1"  // All protocols
  }
}
```