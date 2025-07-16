#!/usr/bin/env python3
"""
Add IP to Security Group via JSON Parameter
This script accepts a JSON parameter to add IP rules to AWS security groups
"""

import boto3
import sys
import json
import argparse
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from datetime import datetime

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
    python add_sg_rule_json.py '{"UserName":"chris_test","UserIP":"1.1.1.1","Port":"8081","SecurityGroupID":"sg-0f0df629567eb6344","ResourceName":"DevEC2"}'
        '''
    )
    
    parser.add_argument(
        'json_config',
        help='JSON configuration string with UserName, UserIP, Port, SecurityGroupID, and ResourceName'
    )
    
    return parser.parse_args()

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
    
    # Validate port is numeric
    try:
        port = int(config['Port'])
        if port < 1 or port > 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
    except ValueError:
        raise ValueError(f"Port must be a valid number, got '{config['Port']}'")
    
    return config

def add_security_group_rule(config):
    """
    Add IP address rule to security group
    
    Args:
        config (dict): Configuration dictionary with required fields
    
    Returns:
        bool: True if successful, False otherwise
    """
    # AWS Credentials
    access_key = 'AKIAXEFUNA23JDGJOV67'
    secret_key = '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'
    
    # Extract configuration
    username = config['UserName']
    ip_address = config['UserIP']
    port = int(config['Port'])
    security_group_id = config['SecurityGroupID']
    resource_name = config['ResourceName']
    
    # Add /32 to single IP if not already present
    if '/' not in ip_address:
        ip_address = f"{ip_address}/32"
    
    # Generate timestamp in YYYYMMDD-HHMM format
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    
    # Format description: {ResourceName} - {Port}-auto-{username}-YYYYMMDD-HHMM
    access_name = f"{resource_name} - {port}"
    description = f"{access_name}-auto-{username}-{timestamp}"
    
    try:
        # Create EC2 client
        print("Creating EC2 client...")
        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='us-east-1'
        )
        
        # Get security group details
        print(f"\nFetching security group: {security_group_id}")
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
        print(f"\nAdding new inbound rule:")
        print(f"  Resource Name: {resource_name}")
        print(f"  User Name: {username}")
        print(f"  IP Address: {ip_address}")
        print(f"  Port: {port}")
        print(f"  Description: {description}")
        
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
            print("\nSUCCESS: Rule added successfully!")
            
            # Show all rules for this port
            response = ec2_client.describe_security_groups(
                GroupIds=[security_group_id]
            )
            
            sg = response['SecurityGroups'][0]
            print(f"\nAll rules for port {port}:")
            for rule in sg.get('IpPermissions', []):
                if rule.get('FromPort') == port and rule.get('ToPort') == port:
                    for ip_range in rule.get('IpRanges', []):
                        marker = " [NEW]" if ip_range.get('CidrIp') == ip_address else ""
                        print(f"  - {ip_range.get('CidrIp')} | {ip_range.get('Description', 'No description')}{marker}")
            
            return True
        else:
            print("ERROR: Failed to add rule")
            return False
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"\nERROR: AWS Client Error - {error_code}: {error_message}")
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
    print("=== AWS Security Group Rule Manager (JSON) ===")
    print("=" * 46)
    
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Validate and parse JSON
        print("Parsing JSON configuration...")
        config = validate_json_config(args.json_config)
        
        print("\nConfiguration:")
        print(f"  User Name: {config['UserName']}")
        print(f"  User IP: {config['UserIP']}")
        print(f"  Port: {config['Port']}")
        print(f"  Security Group ID: {config['SecurityGroupID']}")
        print(f"  Resource Name: {config['ResourceName']}")
        
        # Add the security group rule
        success = add_security_group_rule(config)
        
        if success:
            print(f"\nSUCCESS: Completed processing rule for {config['UserIP']}!")
            sys.exit(0)
        else:
            print(f"\nFAILED: Could not process rule for {config['UserIP']}!")
            sys.exit(1)
            
    except ValueError as e:
        print(f"\nERROR: Configuration error - {e}")
        print("\nUsage example:")
        print('python add_sg_rule_json.py \'{"UserName":"chris_test","UserIP":"1.1.1.1","Port":"8081","SecurityGroupID":"sg-0f0df629567eb6344","ResourceName":"DevEC2"}\'')
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
