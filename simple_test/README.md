# AWS Security Group Whitelist Management

## Project Overview
This project provides Python scripts for managing AWS EC2 Security Group rules, specifically for whitelisting IP addresses with proper access control and documentation.

## Prerequisites
- Python 3.x installed
- boto3 library (`pip install boto3`)
- AWS credentials with EC2 security group management permissions

## Scripts Overview

### 1. test_aws_access.py
- **Purpose**: Test AWS credentials and connectivity
- **Function**: Lists all security groups accessible with the provided credentials
- **Usage**: `python test_aws_access.py`

### 2. add_ip_to_sg.py
- **Purpose**: Add IP address to security group with common ports (22, 80, 443, 3389)
- **Function**: Adds rules for SSH, HTTP, HTTPS, and RDP access
- **Usage**: Hardcoded for specific IP and security group

### 3. add_ip_to_sg_v2.py
- **Purpose**: Improved version with better error handling and duplicate detection
- **Function**: Checks existing rules before adding new ones
- **Usage**: Hardcoded configuration

### 4. update_sg_description.py
- **Purpose**: Update descriptions for existing security group rules
- **Function**: Removes and re-adds rules with new descriptions
- **Usage**: Updates all rules for a specific IP address

### 5. add_port_8080_rule.py
- **Purpose**: Add specific port rule with formatted description
- **Function**: Adds rule for port 8080 with timestamp-based description
- **Usage**: Hardcoded for specific configuration

### 6. add_ip_1111_to_sg.py
- **Purpose**: Add IP 1.1.1.1 to security group for port 8080
- **Function**: Demonstrates adding different IPs to same port
- **Usage**: Hardcoded configuration

### 7. add_sg_rule_json.py ⭐ (Recommended)
- **Purpose**: Flexible script accepting JSON parameters
- **Function**: Add any IP/port combination via command-line JSON
- **Usage**: `python add_sg_rule_json.py '{"UserName":"user","UserIP":"x.x.x.x","Port":"xxxx","SecurityGroupID":"sg-xxx","ResourceName":"Resource"}'`

## Configuration

### AWS Credentials
All scripts use embedded AWS credentials:
- **Access Key**: AKIAXEFUNA23JDGJOV67
- **Secret Key**: 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
- **Region**: us-east-1

⚠️ **Security Note**: For production use, consider using AWS IAM roles, environment variables, or AWS credentials file instead of hardcoded credentials.

### Description Format
Rules are created with descriptions following this pattern:
```
{ResourceName} - {Port}-auto-{UserName}-YYYYMMDD-HHMM
```

Example: `DevEC2 - 8080-auto-chris_test-20250711-1326`

## Examples

### Test AWS Access
```bash
python test_aws_access.py
```

### Add Rule Using JSON Parameters
```bash
python add_sg_rule_json.py '{"UserName":"chris_test","UserIP":"1.1.1.1","Port":"8081","SecurityGroupID":"sg-0f0df629567eb6344","ResourceName":"DevEC2"}'
```

### Update Rule Descriptions
```bash
python update_sg_description.py
```

## Security Group Information
- **Dev Security Group ID**: sg-0f0df629567eb6344
- **Security Group Name**: whm-dev
- **VPC ID**: vpc-0957f6238229e387a

## Common Ports
- **22**: SSH
- **80**: HTTP
- **443**: HTTPS
- **3389**: RDP
- **8080-8081**: Custom application ports

## Error Handling
All scripts include comprehensive error handling for:
- Invalid credentials
- Missing permissions
- Duplicate rules
- Network connectivity issues
- Invalid input parameters

## Best Practices
1. Always verify rules after adding them
2. Use descriptive names in the description field
3. Check for existing rules before adding new ones
4. Use the JSON-based script for flexibility
5. Maintain an audit trail with timestamps in descriptions

## Troubleshooting
- **Permission Denied**: Ensure AWS credentials have `ec2:AuthorizeSecurityGroupIngress` permission
- **Duplicate Rule**: Script will skip if rule already exists
- **Invalid JSON**: Check JSON format and required fields
- **Connection Error**: Verify network connectivity and AWS region

## Future Enhancements
- Add rule removal functionality
- Implement bulk operations
- Create web interface
- Add logging to file
- Support for multiple regions
- Integration with AWS SSO