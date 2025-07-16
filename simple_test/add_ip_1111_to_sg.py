#!/usr/bin/env python3
"""
Add IP 1.1.1.1 to Security Group for Port 8080
This script adds a new IP address to an EC2 security group with formatted description
"""

import boto3
import sys
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from datetime import datetime

def add_ip_to_port(security_group_id, ip_address, port, access_name, username):
    """
    Add a new IP address rule to a security group for a specific port
    
    Args:
        security_group_id (str): The ID of the security group
        ip_address (str): The IP address to whitelist
        port (int): The port number to open
        access_name (str): The access name for the description
        username (str): The username for the description
    
    Returns:
        bool: True if successful, False otherwise
    """
    # AWS Credentials
    access_key = 'AKIAXEFUNA23JDGJOV67'
    secret_key = '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'
    
    # Add /32 to single IP if not already present
    if '/' not in ip_address:
        ip_address = f"{ip_address}/32"
    
    # Generate timestamp in YYYYMMDD-HHMM format
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    
    # Format description according to pattern: {Access Name}-auto-{username}-YYYYMMDD-HHMM
    description = f"{access_name}-auto-{username}-{timestamp}"
    
    try:
        # Create EC2 client with explicit credentials
        print("Creating EC2 client with provided credentials...")
        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='us-east-1'  # Default region
        )
        
        # Get current security group details
        print(f"\nFetching security group details: {security_group_id}")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        if not response['SecurityGroups']:
            print(f"ERROR: Security group {security_group_id} not found")
            return False
        
        sg = response['SecurityGroups'][0]
        print(f"Security Group Name: {sg.get('GroupName', 'N/A')}")
        print(f"VPC ID: {sg.get('VpcId', 'N/A')}")
        
        # Check if rule already exists for this IP and port
        print(f"\nChecking if rule already exists for {ip_address} on port {port}...")
        rule_exists = False
        existing_description = None
        
        for rule in sg.get('IpPermissions', []):
            if rule.get('FromPort') == port and rule.get('ToPort') == port:
                for ip_range in rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == ip_address:
                        rule_exists = True
                        existing_description = ip_range.get('Description', 'No description')
                        break
        
        if rule_exists:
            print(f"Rule already exists for {ip_address} on port {port}")
            print(f"Existing description: {existing_description}")
            print("Skipping rule creation to avoid duplicate")
            return True
        
        # Display existing rules for this port
        print(f"\nExisting rules for port {port}:")
        found_port_rules = False
        for rule in sg.get('IpPermissions', []):
            if rule.get('FromPort') == port and rule.get('ToPort') == port:
                found_port_rules = True
                for ip_range in rule.get('IpRanges', []):
                    print(f"  - {ip_range.get('CidrIp')} | {ip_range.get('Description', 'No description')}")
        
        if not found_port_rules:
            print("  No existing rules for this port")
        
        # Create the new rule
        print(f"\nAdding new inbound rule:")
        print(f"  IP Address: {ip_address}")
        print(f"  Port: {port}")
        print(f"  Protocol: TCP")
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
            print("\nSUCCESS: Inbound rule added successfully!")
        else:
            print("\nERROR: Failed to add inbound rule")
            return False
        
        # Verify the rule was added and show all rules for this port
        print("\nVerifying the new rule was added...")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        sg = response['SecurityGroups'][0]
        print(f"\nAll inbound rules for port {port}:")
        for rule in sg.get('IpPermissions', []):
            if rule.get('FromPort') == port and rule.get('ToPort') == port:
                for ip_range in rule.get('IpRanges', []):
                    if ip_range.get('CidrIp') == ip_address:
                        print(f"  -> {ip_range.get('CidrIp')} | {ip_range.get('Description')} [NEW]")
                    else:
                        print(f"  - {ip_range.get('CidrIp')} | {ip_range.get('Description', 'No description')}")
        
        return True
        
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
    # Configuration
    security_group_id = 'sg-0f0df629567eb6344'  # whm-dev
    ip_address = '1.1.1.1'
    port = 8080
    access_name = 'DevEC2 - 8080'
    username = 'Chris_test'
    
    print("=== Add IP to Security Group Inbound Rules ===")
    print(f"Security Group ID: {security_group_id}")
    print(f"IP Address to Add: {ip_address}")
    print(f"Port: {port}")
    print(f"Access Name: {access_name}")
    print(f"Username: {username}")
    print("=" * 46)
    
    success = add_ip_to_port(security_group_id, ip_address, port, access_name, username)
    
    if success:
        print(f"\nSUCCESS: IP address {ip_address} has been added to port {port}!")
        sys.exit(0)
    else:
        print(f"\nFAILED: Could not add IP address {ip_address} to port {port}!")
        sys.exit(1)

if __name__ == "__main__":
    main()
