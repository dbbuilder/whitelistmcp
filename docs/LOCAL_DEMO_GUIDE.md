# AWS Whitelisting MCP Server - Local Demo Guide

This guide walks you through setting up and testing the AWS Whitelisting MCP Server locally, including minimal AWS setup requirements.

## Platform Notes

This guide includes commands for different platforms:
- **Linux/macOS/WSL**: Standard Unix commands
- **Windows PowerShell**: PowerShell equivalents
- **Windows Command Prompt**: CMD equivalents

Choose the commands that match your environment.

## Prerequisites

### 1. AWS Account Setup

You'll need the following from AWS:

#### Option A: IAM User (Simplest for testing)
1. **Create an IAM User**:
   - Go to AWS Console → IAM → Users → Add User
   - User name: `mcp-whitelist-demo`
   - Access type: ✅ Programmatic access
   - Click "Next"

2. **Attach Permissions**:
   - Select "Attach existing policies directly"
   - Search and select: `AmazonEC2FullAccess` (for testing only)
   - For production, create a custom policy with minimal permissions (see below)
   - Click "Next" → "Create user"

3. **Save Credentials**:
   - Access key ID: `AKIAIOSFODNN7EXAMPLE`
   - Secret access key: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
   - ⚠️ Save these securely - you won't see the secret key again!

#### Option B: Minimal IAM Policy (Recommended)
Create a custom policy with only the required permissions:

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
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. Create a Test Security Group

1. Go to AWS Console → EC2 → Security Groups
2. Click "Create security group"
3. Settings:
   - Name: `mcp-test-sg`
   - Description: `Test security group for MCP demo`
   - VPC: Select your default VPC
4. Click "Create security group"
5. Note the Security Group ID: `sg-0123456789abcdef0`

## Local Setup

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/dbbuilder/whitelistmcp2.git
cd whitelistmcp2

# Create virtual environment
# Linux/macOS/WSL:
python3 -m venv venv

# Windows (if python3 command not available):
python -m venv venv

# Activate virtual environment
# Linux/macOS/WSL:
source venv/bin/activate

# Windows Command Prompt:
venv\Scripts\activate

# Windows PowerShell:
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Create Test Configuration

Create a file `demo_config.json`:

```json
{
  "credential_profiles": [],
  "default_parameters": {
    "region": "us-east-1",
    "port": 22,
    "protocol": "tcp",
    "description_template": "Added by {user} on {date} - Demo"
  },
  "security_settings": {
    "require_mfa": false,
    "allowed_ip_ranges": [],
    "max_rule_duration_hours": 0,
    "rate_limit_per_minute": 60,
    "enable_audit_logging": true
  },
  "port_mappings": [
    {"name": "ssh", "port": 22, "description": "SSH access"},
    {"name": "http", "port": 80, "description": "HTTP traffic"},
    {"name": "https", "port": 443, "description": "HTTPS traffic"},
    {"name": "rdp", "port": 3389, "description": "Remote Desktop"}
  ]
}
```

## Testing the Server

### 1. Start the MCP Server

In one terminal:
```bash
python -m whitelistmcp.main -c demo_config.json -v
```

The server is now waiting for JSON-RPC requests on stdin.

### 2. Test Requests

In another terminal, create test request files:

#### Test 1: Add Your Current IP

Create `add_current_ip.json`:
```json
{
  "jsonrpc": "2.0",
  "id": "demo-add-1",
  "method": "whitelist/add",
  "params": {
    "credentials": {
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "secret_access_key": "YOUR_SECRET_ACCESS_KEY",
      "region": "us-east-1"
    },
    "security_group_id": "sg-0123456789abcdef0",
    "ip_address": "current",
    "port": "ssh",
    "protocol": "tcp",
    "description": "Demo SSH access from current IP"
  }
}
```

Send the request:

**Linux/macOS/WSL:**
```bash
cat add_current_ip.json | python -m whitelistmcp.main -c demo_config.json
```

**Windows PowerShell:**
```powershell
Get-Content add_current_ip.json | python -m whitelistmcp.main -c demo_config.json
```

**Windows Command Prompt:**
```cmd
type add_current_ip.json | python -m whitelistmcp.main -c demo_config.json
```

Expected response:
```json
{
  "jsonrpc": "2.0",
  "id": "demo-add-1",
  "result": {
    "success": true,
    "message": "Rule added successfully to sg-0123456789abcdef0",
    "rule": {
      "group_id": "sg-0123456789abcdef0",
      "cidr_ip": "203.0.113.45/32",
      "port": 22,
      "protocol": "tcp",
      "description": "Demo SSH access from current IP"
    }
  }
}
```

#### Test 2: List Rules

Create `list_rules.json`:
```json
{
  "jsonrpc": "2.0",
  "id": "demo-list-1",
  "method": "whitelist/list",
  "params": {
    "credentials": {
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "secret_access_key": "YOUR_SECRET_ACCESS_KEY",
      "region": "us-east-1"
    },
    "security_group_id": "sg-0123456789abcdef0"
  }
}
```

Send the request:

**Linux/macOS/WSL:**
```bash
cat list_rules.json | python -m whitelistmcp.main -c demo_config.json
```

**Windows PowerShell:**
```powershell
Get-Content list_rules.json | python -m whitelistmcp.main -c demo_config.json
```

**Windows Command Prompt:**
```cmd
type list_rules.json | python -m whitelistmcp.main -c demo_config.json
```

#### Test 3: Add Specific IP Range

Create `add_ip_range.json`:
```json
{
  "jsonrpc": "2.0",
  "id": "demo-add-2",
  "method": "whitelist/add",
  "params": {
    "credentials": {
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "secret_access_key": "YOUR_SECRET_ACCESS_KEY",
      "region": "us-east-1"
    },
    "security_group_id": "sg-0123456789abcdef0",
    "ip_address": "10.0.0.0/24",
    "port": 443,
    "protocol": "tcp",
    "description": "Internal network HTTPS access"
  }
}
```

#### Test 4: Check if Rule Exists

Create `check_rule.json`:
```json
{
  "jsonrpc": "2.0",
  "id": "demo-check-1",
  "method": "whitelist/check",
  "params": {
    "credentials": {
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "secret_access_key": "YOUR_SECRET_ACCESS_KEY",
      "region": "us-east-1"
    },
    "security_group_id": "sg-0123456789abcdef0",
    "ip_address": "10.0.0.0/24",
    "port": 443,
    "protocol": "tcp"
  }
}
```

#### Test 5: Remove a Rule

Create `remove_rule.json`:
```json
{
  "jsonrpc": "2.0",
  "id": "demo-remove-1",
  "method": "whitelist/remove",
  "params": {
    "credentials": {
      "access_key_id": "YOUR_ACCESS_KEY_ID",
      "secret_access_key": "YOUR_SECRET_ACCESS_KEY",
      "region": "us-east-1"
    },
    "security_group_id": "sg-0123456789abcdef0",
    "ip_address": "10.0.0.0/24",
    "port": 443,
    "protocol": "tcp"
  }
}
```

### 3. Interactive Testing Script

Create `demo_interactive.py` (save this as a file):
```python
#!/usr/bin/env python3
import json
import subprocess
import sys

def send_request(request):
    """Send request to MCP server and get response."""
    proc = subprocess.Popen(
        ['python', '-m', 'whitelistmcp.main', '-c', 'demo_config.json'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = proc.communicate(json.dumps(request))
    
    if stderr:
        print(f"Error: {stderr}", file=sys.stderr)
    
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        print(f"Invalid response: {stdout}")
        return None

def main():
    # Replace with your actual AWS credentials
    ACCESS_KEY = input("Enter AWS Access Key ID: ")
    SECRET_KEY = input("Enter AWS Secret Access Key: ")
    SG_ID = input("Enter Security Group ID (e.g., sg-0123456789abcdef0): ")
    
    credentials = {
        "access_key_id": ACCESS_KEY,
        "secret_access_key": SECRET_KEY,
        "region": "us-east-1"
    }
    
    while True:
        print("\n=== MCP Demo Menu ===")
        print("1. Add current IP for SSH")
        print("2. Add custom IP/CIDR")
        print("3. List all rules")
        print("4. Check if rule exists")
        print("5. Remove a rule")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ")
        
        if choice == '1':
            response = send_request({
                "jsonrpc": "2.0",
                "id": "interactive-1",
                "method": "whitelist/add",
                "params": {
                    "credentials": credentials,
                    "security_group_id": SG_ID,
                    "ip_address": "current",
                    "port": "ssh",
                    "description": "Interactive demo SSH access"
                }
            })
            print(json.dumps(response, indent=2))
            
        elif choice == '2':
            ip = input("Enter IP or CIDR (e.g., 192.168.1.0/24): ")
            port = input("Enter port number or name (e.g., 443 or https): ")
            desc = input("Enter description: ")
            
            response = send_request({
                "jsonrpc": "2.0",
                "id": "interactive-2",
                "method": "whitelist/add",
                "params": {
                    "credentials": credentials,
                    "security_group_id": SG_ID,
                    "ip_address": ip,
                    "port": port,
                    "description": desc
                }
            })
            print(json.dumps(response, indent=2))
            
        elif choice == '3':
            response = send_request({
                "jsonrpc": "2.0",
                "id": "interactive-3",
                "method": "whitelist/list",
                "params": {
                    "credentials": credentials,
                    "security_group_id": SG_ID
                }
            })
            print(json.dumps(response, indent=2))
            
        elif choice == '4':
            ip = input("Enter IP or CIDR to check: ")
            port = input("Enter port: ")
            
            response = send_request({
                "jsonrpc": "2.0",
                "id": "interactive-4",
                "method": "whitelist/check",
                "params": {
                    "credentials": credentials,
                    "security_group_id": SG_ID,
                    "ip_address": ip,
                    "port": port
                }
            })
            print(json.dumps(response, indent=2))
            
        elif choice == '5':
            ip = input("Enter IP or CIDR to remove: ")
            port = input("Enter port: ")
            
            response = send_request({
                "jsonrpc": "2.0",
                "id": "interactive-5",
                "method": "whitelist/remove",
                "params": {
                    "credentials": credentials,
                    "security_group_id": SG_ID,
                    "ip_address": ip,
                    "port": port
                }
            })
            print(json.dumps(response, indent=2))
            
        elif choice == '6':
            break

if __name__ == "__main__":
    main()
```

Make it executable and run:

**Linux/macOS/WSL:**
```bash
chmod +x demo_interactive.py
./demo_interactive.py
```

**Windows:**
```cmd
python demo_interactive.py
```

## Docker Testing

### 1. Build and Run with Docker

```bash
# Build the image
docker-compose build

# Run interactive demo
docker run -it --rm whitelistmcp:latest python -m whitelistmcp.main -v
```

### 2. Docker Compose Testing

Create `docker-test-request.json` and run:

**Linux/macOS/WSL:**
```bash
cat docker-test-request.json | docker-compose run --rm whitelistmcp
```

**Windows PowerShell:**
```powershell
Get-Content docker-test-request.json | docker-compose run --rm whitelistmcp
```

**Windows Command Prompt:**
```cmd
type docker-test-request.json | docker-compose run --rm whitelistmcp
```

## Verifying in AWS Console

1. Go to AWS Console → EC2 → Security Groups
2. Find your test security group
3. Click on "Inbound rules" tab
4. You should see the rules added by the MCP server

## Troubleshooting

### Common Issues

1. **Authentication Error**:
   - Verify your AWS credentials are correct
   - Check the region matches where your security group exists
   - Ensure your IAM user has the required permissions

2. **Security Group Not Found**:
   - Verify the security group ID is correct
   - Ensure the security group exists in the specified region

3. **Current IP Detection Failed**:
   - The server tries multiple services to detect your IP
   - If behind a corporate proxy, manually specify your public IP

### Debug Mode

Run with verbose logging:

**Linux/macOS/WSL:**
```bash
python -m whitelistmcp.main -c demo_config.json -v 2>&1 | tee debug.log
```

**Windows PowerShell:**
```powershell
python -m whitelistmcp.main -c demo_config.json -v 2>&1 | Tee-Object -FilePath debug.log
```

**Windows Command Prompt:**
```cmd
python -m whitelistmcp.main -c demo_config.json -v > debug.log 2>&1
```

## Cleanup

### Remove Test Rules

List all rules first:

**Linux/macOS/WSL:**
```bash
cat list_rules.json | python -m whitelistmcp.main -c demo_config.json
```

**Windows PowerShell:**
```powershell
Get-Content list_rules.json | python -m whitelistmcp.main -c demo_config.json
```

**Windows Command Prompt:**
```cmd
type list_rules.json | python -m whitelistmcp.main -c demo_config.json
```

Then remove specific rules using the remove_rule.json template.

### Delete Test Security Group
1. Remove all inbound rules first
2. AWS Console → EC2 → Security Groups
3. Select your test group → Actions → Delete security group

### Delete IAM User (if created for testing)
1. AWS Console → IAM → Users
2. Select the test user → Delete user

## Security Notes

- Never commit AWS credentials to version control
- Use environment variables or AWS credentials file in production
- Apply principle of least privilege for IAM policies
- Consider using AWS IAM roles instead of long-lived credentials
- Enable MFA for production use
- Regularly rotate access keys