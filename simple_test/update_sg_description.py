#!/usr/bin/env python3
"""
Update Security Group Rule Description
This script updates the description for existing IP rules by removing and re-adding them
"""

import boto3
import sys
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from datetime import datetime

def update_ip_rule_description(security_group_id, ip_address, new_description):
    """
    Update the description for an IP address in security group rules
    
    Args:
        security_group_id (str): The ID of the security group
        ip_address (str): The IP address to update
        new_description (str): New description for the rules
    
    Returns:
        bool: True if successful, False otherwise
    """
    # AWS Credentials
    access_key = 'AKIAXEFUNA23JDGJOV67'
    secret_key = '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'
    
    # Add /32 to single IP if not already present
    if '/' not in ip_address:
        ip_address = f"{ip_address}/32"
    
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
        print(f"\nFetching current rules for security group: {security_group_id}")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        if not response['SecurityGroups']:
            print(f"ERROR: Security group {security_group_id} not found")
            return False
        
        sg = response['SecurityGroups'][0]
        print(f"Security Group Name: {sg.get('GroupName', 'N/A')}")
        print(f"VPC ID: {sg.get('VpcId', 'N/A')}")
        
        # Find all rules for this IP
        rules_to_update = []
        for rule in sg.get('IpPermissions', []):
            for ip_range in rule.get('IpRanges', []):
                if ip_range.get('CidrIp') == ip_address:
                    rules_to_update.append({
                        'protocol': rule.get('IpProtocol'),
                        'from_port': rule.get('FromPort'),
                        'to_port': rule.get('ToPort'),
                        'old_description': ip_range.get('Description', 'No description')
                    })
        
        if not rules_to_update:
            print(f"\nNo rules found for IP address: {ip_address}")
            return False
        
        print(f"\nFound {len(rules_to_update)} rule(s) for {ip_address}")
        for rule in rules_to_update:
            print(f"  Port: {rule['from_port']}-{rule['to_port']} ({rule['protocol']})")
            print(f"  Current Description: {rule['old_description']}")
        
        # First, revoke the existing rules
        print("\nStep 1: Removing existing rules...")
        for rule in rules_to_update:
            revoke_rule = {
                'IpProtocol': rule['protocol'],
                'FromPort': rule['from_port'],
                'ToPort': rule['to_port'],
                'IpRanges': [{'CidrIp': ip_address}]
            }
            
            try:
                ec2_client.revoke_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=[revoke_rule]
                )
                print(f"  Removed rule for port {rule['from_port']}")
            except ClientError as e:
                print(f"  ERROR removing rule for port {rule['from_port']}: {e.response['Error']['Message']}")
        
        # Now add the rules back with the new description
        print(f"\nStep 2: Adding rules back with new description: '{new_description}'")
        
        # Map common ports to service names
        port_services = {
            22: 'SSH',
            80: 'HTTP',
            443: 'HTTPS',
            3389: 'RDP'
        }
        
        for rule in rules_to_update:
            port = rule['from_port']
            service = port_services.get(port, f'Port {port}')
            
            new_rule = {
                'IpProtocol': rule['protocol'],
                'FromPort': rule['from_port'],
                'ToPort': rule['to_port'],
                'IpRanges': [{'CidrIp': ip_address, 'Description': f'{service} - {new_description}'}]
            }
            
            try:
                ec2_client.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=[new_rule]
                )
                print(f"  Added rule for port {port} ({service}) with new description")
            except ClientError as e:
                print(f"  ERROR adding rule for port {port}: {e.response['Error']['Message']}")
        
        # Verify the final state
        print("\nStep 3: Verifying updated rules...")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        sg = response['SecurityGroups'][0]
        print(f"\nUpdated rules for {ip_address}:")
        for rule in sg.get('IpPermissions', []):
            for ip_range in rule.get('IpRanges', []):
                if ip_range.get('CidrIp') == ip_address:
                    print(f"  Port: {rule.get('FromPort')}-{rule.get('ToPort')} "
                          f"({rule.get('IpProtocol')})")
                    print(f"  Description: {ip_range.get('Description', 'No description')}")
                    print("  ---")
        
        return True
        
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
    ip_address = '73.19.9.193'
    new_description = 'test_Chris_IP'
    
    print("=== Update Security Group Rule Description ===")
    print(f"Security Group ID: {security_group_id}")
    print(f"IP Address: {ip_address}")
    print(f"New Description: {new_description}")
    print("=" * 45)
    
    success = update_ip_rule_description(security_group_id, ip_address, new_description)
    
    if success:
        print("\nSUCCESS: Rule descriptions have been updated!")
        sys.exit(0)
    else:
        print("\nFAILED: Could not update rule descriptions!")
        sys.exit(1)

if __name__ == "__main__":
    main()
