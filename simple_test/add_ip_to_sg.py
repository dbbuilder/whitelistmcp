#!/usr/bin/env python3
"""
Add IP to AWS Security Group
This script adds an IP address to an EC2 security group's ingress rules
"""

import boto3
import sys
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from datetime import datetime

def add_ip_to_security_group(security_group_id, ip_address, description=None):
    """
    Add an IP address to a security group's ingress rules
    
    Args:
        security_group_id (str): The ID of the security group
        ip_address (str): The IP address to whitelist
        description (str): Optional description for the rule
    
    Returns:
        bool: True if successful, False otherwise
    """
    # AWS Credentials
    access_key = 'AKIAXEFUNA23JDGJOV67'
    secret_key = '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'
    
    # Add /32 to single IP if not already present
    if '/' not in ip_address:
        ip_address = f"{ip_address}/32"
    
    # Set default description if not provided
    if description is None:
        description = f"Added via API on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        # Create EC2 client with explicit credentials
        print("Creating EC2 client with provided credentials...")
        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='us-east-1'  # Default region
        )
        
        # First, get current security group details
        print(f"\nFetching current rules for security group: {security_group_id}")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        if not response['SecurityGroups']:
            print(f"ERROR: Security group {security_group_id} not found")
            return False
        
        sg = response['SecurityGroups'][0]
        print(f"Security Group Name: {sg.get('GroupName', 'N/A')}")
        print(f"Description: {sg.get('Description', 'N/A')}")
        print(f"VPC ID: {sg.get('VpcId', 'N/A')}")
        
        # Display current ingress rules
        print("\nCurrent Ingress Rules:")
        for rule in sg.get('IpPermissions', []):
            print(f"  Protocol: {rule.get('IpProtocol', 'N/A')}")
            if rule.get('FromPort'):
                print(f"  Port Range: {rule.get('FromPort')} - {rule.get('ToPort')}")
            for ip_range in rule.get('IpRanges', []):
                print(f"  CIDR: {ip_range.get('CidrIp')} - {ip_range.get('Description', 'No description')}")
            print("  ---")
        
        # Define the new ingress rules
        # Adding common ports: SSH (22), HTTP (80), HTTPS (443), and RDP (3389)
        new_rules = [
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': ip_address, 'Description': f'SSH - {description}'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': ip_address, 'Description': f'HTTP - {description}'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 443,
                'ToPort': 443,
                'IpRanges': [{'CidrIp': ip_address, 'Description': f'HTTPS - {description}'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 3389,
                'ToPort': 3389,
                'IpRanges': [{'CidrIp': ip_address, 'Description': f'RDP - {description}'}]
            }
        ]
        
        # Add the ingress rules
        print(f"\nAdding ingress rules for IP: {ip_address}")
        print("Ports to be opened: 22 (SSH), 80 (HTTP), 443 (HTTPS), 3389 (RDP)")
        
        response = ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=new_rules
        )
        
        print("\n✓ Successfully added ingress rules!")
        print(f"Response: {response['Return']}")
        
        # Verify the rules were added
        print("\nVerifying new rules...")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        sg = response['SecurityGroups'][0]
        print("\nUpdated Ingress Rules:")
        for rule in sg.get('IpPermissions', []):
            for ip_range in rule.get('IpRanges', []):
                if ip_address in ip_range.get('CidrIp', ''):
                    print(f"  ✓ Protocol: {rule.get('IpProtocol')}, "
                          f"Ports: {rule.get('FromPort')}-{rule.get('ToPort')}, "
                          f"CIDR: {ip_range.get('CidrIp')}")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"\nERROR: AWS Client Error - {error_code}: {error_message}")
        
        if error_code == 'InvalidPermission.Duplicate':
            print("The rule already exists in the security group.")
        elif error_code == 'UnauthorizedOperation':
            print("The credentials do not have permission to modify this security group.")
        elif error_code == 'InvalidGroup.NotFound':
            print("The specified security group does not exist.")
            
        return False
        
    except Exception as e:
        print(f"\nERROR: Unexpected error - {str(e)}")
        return False

def main():
    """
    Main function
    """
    # Configuration
    security_group_id = 'sg-0f0df629567eb6344'  # whm-dev
    ip_address = '73.19.9.193'
    description = 'External IP whitelist'
    
    print("=== AWS Security Group IP Whitelist ===")
    print(f"Security Group ID: {security_group_id}")
    print(f"IP Address to Add: {ip_address}")
    print(f"Description: {description}")
    print("=" * 40)
    
    success = add_ip_to_security_group(security_group_id, ip_address, description)
    
    if success:
        print("\n✓ IP address successfully added to security group!")
        sys.exit(0)
    else:
        print("\n✗ Failed to add IP address to security group!")
        sys.exit(1)

if __name__ == "__main__":
    main()
