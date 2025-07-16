#!/usr/bin/env python3
"""
Test AWS Access - List Security Groups
This script tests AWS credentials by attempting to list EC2 security groups
"""

import boto3
import sys
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

def test_aws_access():
    """
    Test AWS access by listing EC2 security groups
    """
    # AWS Credentials
    access_key = 'AKIAXEFUNA23JDGJOV67'
    secret_key = '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'
    
    try:
        # Create EC2 client with explicit credentials
        print("Creating EC2 client with provided credentials...")
        ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='us-east-1'  # Default region, adjust if needed
        )
        
        # Test connection by listing security groups
        print("\nAttempting to list security groups...")
        response = ec2_client.describe_security_groups()
        
        # Display results
        security_groups = response.get('SecurityGroups', [])
        print(f"\nSuccessfully connected to AWS!")
        print(f"Found {len(security_groups)} security group(s):\n")
        
        for sg in security_groups:
            print(f"Security Group ID: {sg['GroupId']}")
            print(f"  Name: {sg.get('GroupName', 'N/A')}")
            print(f"  Description: {sg.get('Description', 'N/A')}")
            print(f"  VPC ID: {sg.get('VpcId', 'N/A')}")
            print("-" * 50)
        
        return True
        
    except NoCredentialsError:
        print("ERROR: No credentials found")
        return False
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"ERROR: AWS Client Error - {error_code}: {error_message}")
        
        # Check for specific error types
        if error_code == 'AuthFailure':
            print("The provided credentials are invalid or do not have necessary permissions.")
        elif error_code == 'UnauthorizedOperation':
            print("The credentials do not have permission to perform this operation.")
        elif error_code == 'InvalidUserID.NotFound':
            print("The AWS access key ID provided does not exist.")
            
        return False
        
    except BotoCoreError as e:
        print(f"ERROR: BotoCore Error - {str(e)}")
        return False
        
    except Exception as e:
        print(f"ERROR: Unexpected error - {str(e)}")
        return False

def main():
    """
    Main function
    """
    print("=== AWS Access Test - Security Groups ===")
    print(f"Username: agent-auth-dev")
    print(f"Access Key: AKIAXEFUNA23JDGJOV67")
    print("=" * 40)
    
    success = test_aws_access()
    
    if success:
        print("\n✓ AWS access test completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ AWS access test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
