#!/usr/bin/env python3
"""
Add IP to AWS Security Group - Modified version
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
        
        # First, check which ports already have rules for this IP
        print(f"\nChecking existing rules for IP {ip_address}...")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        if not response['SecurityGroups']:
            print(f"ERROR: Security group {security_group_id} not found")
            return False
        
        sg = response['SecurityGroups'][0]
        print(f"Security Group Name: {sg.get('GroupName', 'N/A')}")
        print(f"VPC ID: {sg.get('VpcId', 'N/A')}")
        
        # Check which ports already have rules for this IP
        existing_ports = set()
        for rule in sg.get('IpPermissions', []):
            for ip_range in rule.get('IpRanges', []):
                if ip_range.get('CidrIp') == ip_address:
                    if rule.get('FromPort') == rule.get('ToPort'):
                        existing_ports.add(rule.get('FromPort'))
                    print(f"  Found existing rule: Port {rule.get('FromPort')}-{rule.get('ToPort')} ({rule.get('IpProtocol')})")
        
        # Define the rules we want to add
        desired_rules = [
            {'port': 22, 'protocol': 'tcp', 'desc': 'SSH'},
            {'port': 80, 'protocol': 'tcp', 'desc': 'HTTP'},
            {'port': 443, 'protocol': 'tcp', 'desc': 'HTTPS'},
            {'port': 3389, 'protocol': 'tcp', 'desc': 'RDP'}
        ]
        
        # Filter out rules that already exist
        rules_to_add = []
        for rule in desired_rules:
            if rule['port'] not in existing_ports:
                rules_to_add.append({
                    'IpProtocol': rule['protocol'],
                    'FromPort': rule['port'],
                    'ToPort': rule['port'],
                    'IpRanges': [{'CidrIp': ip_address, 'Description': f"{rule['desc']} - {description}"}]
                })
            else:
                print(f"  Port {rule['port']} ({rule['desc']}) already has a rule for {ip_address}")
        
        if not rules_to_add:
            print("\nAll desired ports already have rules for this IP address!")
            return True
        
        # Add the new ingress rules
        print(f"\nAdding new ingress rules for IP: {ip_address}")
        for rule in rules_to_add:
            port = rule['FromPort']
            desc = rule['IpRanges'][0]['Description'].split(' - ')[0]
            print(f"  Adding rule for port {port} ({desc})...")
            
            try:
                response = ec2_client.authorize_security_group_ingress(
                    GroupId=security_group_id,
                    IpPermissions=[rule]
                )
                print(f"    SUCCESS: Added port {port}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'InvalidPermission.Duplicate':
                    print(f"    SKIP: Port {port} already has this rule")
                else:
                    print(f"    ERROR: Failed to add port {port} - {e.response['Error']['Message']}")
        
        # Verify the final state
        print("\nVerifying final rules for IP address...")
        response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id]
        )
        
        sg = response['SecurityGroups'][0]
        print(f"\nRules for {ip_address}:")
        for rule in sg.get('IpPermissions', []):
            for ip_range in rule.get('IpRanges', []):
                if ip_range.get('CidrIp') == ip_address:
                    print(f"  Port: {rule.get('FromPort')}-{rule.get('ToPort')} "
                          f"({rule.get('IpProtocol')}), "
                          f"Description: {ip_range.get('Description', 'No description')}")
        
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
    description = 'External IP whitelist'
    
    print("=== AWS Security Group IP Whitelist ===")
    print(f"Security Group ID: {security_group_id}")
    print(f"IP Address to Add: {ip_address}")
    print(f"Description: {description}")
    print("=" * 40)
    
    success = add_ip_to_security_group(security_group_id, ip_address, description)
    
    if success:
        print("\nSUCCESS: IP address rules have been processed!")
        sys.exit(0)
    else:
        print("\nFAILED: Could not process IP address rules!")
        sys.exit(1)

if __name__ == "__main__":
    main()
