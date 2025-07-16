#!/usr/bin/env python3
"""
Add IP to AWS Security Group via JSON Parameter - Environment Variable Version
This script uses environment variables for configuration
"""

import boto3
import sys
import json
import argparse
import os
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from datetime import datetime
from pathlib import Path

# Add parent directory to path for config_manager
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config_manager import get_config, format_description
    USE_CONFIG_MANAGER = True
except ImportError:
    print("Warning: config_manager not found. Using direct environment variables.")
    USE_CONFIG_MANAGER = False

def parse_arguments():
    """
    Parse command line arguments
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Add IP address to AWS Security Group using JSON configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Example JSON format:
{
    "UserName": "chris_test",
    "UserIP": "1.1.1.1",
    "Port": "8081",
    "SecurityGroupID": "sg-0f0df629567eb6344",
    "ResourceName": "DevEC2"
}

Usage:
    python add_sg_rule_env.py '{"UserName":"chris_test","UserIP":"1.1.1.1","Port":"8081","SecurityGroupID":"sg-0f0df629567eb6344","ResourceName":"DevEC2"}'
    
Environment Variables:
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_DEFAULT_REGION: AWS region (default: us-east-1)
    DEFAULT_SECURITY_GROUP_ID: Default security group if not specified
        '''
    )
    
    parser.add_argument(
        'json_config',
        help='JSON configuration string with UserName, UserIP, Port, SecurityGroupID, and ResourceName'
    )
    
    parser.add_argument(
        '--env-file',
        default='.env',
        help='Path to environment file (default: .env)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    return parser.parse_args()

def load_aws_credentials():
    """
    Load AWS credentials from environment or config manager
    
    Returns:
        dict: AWS credentials
    """
    if USE_CONFIG_MANAGER:
        config = get_config()
        return config.get_aws_client_config()
    else:
        # Fallback to direct environment variables
        return {
            'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            'region_name': os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        }

def validate_json_config(json_str):
    """
    Validate and parse JSON configuration
    
    Args:
        json_str (str): JSON string to parse
    
    Returns:
        dict: Parsed configuration
    
    Raises:
        ValueError: If JSON is invalid or missing required fields
    """
    try:
        config = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    
    # Required fields
    required_fields = ['UserName', 'UserIP', 'Port', 'SecurityGroupID', 'ResourceName']
    
    # Check for missing fields
    missing_fields = [field for field in required_fields if field not in config]
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Apply defaults from environment if available
    if USE_CONFIG_MANAGER:
        config_mgr = get_config()
        if not config.get('SecurityGroupID') and config_mgr.security_group.default_sg_id:
            config['SecurityGroupID'] = config_mgr.security_group.default_sg_id
    
    # Validate port is numeric
    try:
        port = int(config['Port'])
        if USE_CONFIG_MANAGER:
            settings = get_config().validation_settings
            min_port = settings.get('min_port', 1)
            max_port = settings.get('max_port', 65535)
        else:
            min_port = 1
            max_port = 65535
            
        if port < min_port or port > max_port:
            raise ValueError(f"Port must be between {min_port} and {max_port}, got {port}")
    except ValueError:
        raise ValueError(f"Port must be a valid number, got '{config['Port']}'")
    
    return config

def generate_description(config):
    """
    Generate description using environment configuration
    
    Args:
        config (dict): Rule configuration
    
    Returns:
        str: Formatted description
    """
    if USE_CONFIG_MANAGER:
        return format_description(
            config['ResourceName'],
            config['Port'],
            config['UserName']
        )
    else:
        # Fallback to manual formatting
        timestamp = datetime.now().strftime(
            os.getenv('DESCRIPTION_TIMESTAMP_FORMAT', '%Y%m%d-%H%M')
        )
        prefix = os.getenv('DESCRIPTION_PREFIX', 'auto')
        separator = os.getenv('DESCRIPTION_SEPARATOR', '-')
        
        return separator.join([
            f"{config['ResourceName']} {separator} {config['Port']}",
            prefix,
            config['UserName'],
            timestamp
        ])

def add_security_group_rule(config, dry_run=False):
    """
    Add IP address rule to security group
    
    Args:
        config (dict): Configuration dictionary with required fields
        dry_run (bool): If True, only show what would be done
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Load AWS credentials
    aws_config = load_aws_credentials()
    
    if not aws_config.get('aws_access_key_id') or not aws_config.get('aws_secret_access_key'):
        print("ERROR: AWS credentials not found in environment")
        print("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        return False
    
    # Extract configuration
    username = config['UserName']
    ip_address = config['UserIP']
    port = int(config['Port'])
    security_group_id = config['SecurityGroupID']
    resource_name = config['ResourceName']
    
    # Add /32 to single IP if not already present
    if '/' not in ip_address:
        ip_address = f"{ip_address}/32"
    
    # Generate description
    description = generate_description(config)
    
    print(f"\nConfiguration Summary:")
    print(f"  Security Group ID: {security_group_id}")
    print(f"  IP Address: {ip_address}")
    print(f"  Port: {port}")
    print(f"  Description: {description}")
    print(f"  AWS Region: {aws_config['region_name']}")
    
    if dry_run:
        print("\nDRY RUN: No changes will be made")
        return True
    
    try:
        # Create EC2 client
        print("\nCreating EC2 client...")
        ec2_client = boto3.client('ec2', **aws_config)
        
        # Get security group details
        print(f"Fetching security group: {security_group_id}")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        if not response['SecurityGroups']:
            print(f"ERROR: Security group {security_group_id} not found")
            return False
        
        sg = response['SecurityGroups'][0]
        print(f"Security Group Name: {sg.get('GroupName', 'N/A')}")
        print(f"VPC ID: {sg.get('VpcId', 'N/A')}")
        
        # Check if rule already exists
        print(f"\nChecking existing rules for {ip_address} on port {port}...")
        rule_exists = False
        
        for rule in sg.get('IpPermissions', []):
            if rule.get('FromPort') == port and rule.get('ToPort') == port:
                for ip_range in rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == ip_address:
                        rule_exists = True
                        print(f"Rule already exists: {ip_range.get('Description', 'No description')}")
                        break
        
        if rule_exists:
            print("Skipping duplicate rule creation")
            return True
        
        # Create new rule
        print(f"\nAdding new inbound rule...")
        new_rule = {
            'IpProtocol': 'tcp',
            'FromPort': port,
            'ToPort': port,
            'IpRanges': [{'CidrIp': ip_address, 'Description': description}]
        }
        
        # Add the rule
        response = ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[new_rule]
        )
        
        if response['Return']:
            print("SUCCESS: Rule added successfully!")
            
            # Log to audit file if enabled
            if os.getenv('ENABLE_AUDIT_LOG', 'true').lower() == 'true':
                audit_log_path = os.getenv('AUDIT_LOG_PATH', './logs/audit.log')
                os.makedirs(os.path.dirname(audit_log_path), exist_ok=True)
                
                with open(audit_log_path, 'a') as f:
                    audit_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'action': 'add_rule',
                        'security_group_id': security_group_id,
                        'ip_address': ip_address,
                        'port': port,
                        'username': username,
                        'description': description
                    }
                    f.write(json.dumps(audit_entry) + '\n')
            
            return True
        else:
            print("ERROR: Failed to add rule")
            return False
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"\nERROR: AWS Client Error - {error_code}: {error_message}")
        
        if error_code == 'InvalidPermission.Duplicate':
            print("The rule already exists in the security group.")
        elif error_code == 'UnauthorizedOperation':
            print("The credentials do not have permission to modify this security group.")
            
        return False
        
    except Exception as e:
        print(f"\nERROR: Unexpected error - {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    Main function
    """
    print("=== AWS Security Group Rule Manager (Environment Variables) ===")
    print("=" * 63)
    
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Load environment file if using config manager
        if USE_CONFIG_MANAGER and os.path.exists(args.env_file):
            from config_manager import reload_config
            reload_config(args.env_file)
            print(f"Loaded environment from: {args.env_file}")
        
        # Validate and parse JSON
        print("\nParsing JSON configuration...")
        config = validate_json_config(args.json_config)
        
        print("\nConfiguration:")
        print(f"  User Name: {config['UserName']}")
        print(f"  User IP: {config['UserIP']}")
        print(f"  Port: {config['Port']}")
        print(f"  Security Group ID: {config['SecurityGroupID']}")
        print(f"  Resource Name: {config['ResourceName']}")
        
        # Add the security group rule
        success = add_security_group_rule(config, dry_run=args.dry_run)
        
        if success:
            print(f"\nSUCCESS: Completed processing rule for {config['UserIP']}!")
            sys.exit(0)
        else:
            print(f"\nFAILED: Could not process rule for {config['UserIP']}!")
            sys.exit(1)
            
    except ValueError as e:
        print(f"\nERROR: Configuration error - {e}")
        print("\nUsage example:")
        print('python add_sg_rule_env.py \'{"UserName":"chris_test","UserIP":"1.1.1.1","Port":"8081","SecurityGroupID":"sg-0f0df629567eb6344","ResourceName":"DevEC2"}\'')
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
